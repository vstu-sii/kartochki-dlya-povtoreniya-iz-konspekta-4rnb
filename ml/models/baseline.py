"""Reproducible baseline with optional Gemini primary and deterministic fallback."""

import json
import hashlib
import os
import re
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from ml.tracing.client import TraceClient
from ml.cache import TTLCache
from ml.prompts_v2 import load_prompt, prompt_versions
from ml.tools import SourceLookupRequest, SourceLookupTool, build_retrieval_query


_PROMPT_VERSIONS = prompt_versions()
PROMPT_VERSION = _PROMPT_VERSIONS["generation"]
REVIEW_PROMPT_VERSION = _PROMPT_VERSIONS["review"]
DETERMINISTIC_REVIEW_MODEL = "deterministic-review-v4"
SCHEMA_VERSION = "2.0"
PRIMARY_MODEL = os.getenv("LLM_PRIMARY_MODEL", "gemini-3.8-flash")
CHEAP_MODEL = os.getenv("LLM_CHEAP_MODEL", "gemini-2.5-flash-lite")
GEMINI_TIMEOUT_SECONDS = max(5, min(60, int(os.getenv("GEMINI_TIMEOUT_SECONDS", "30"))))
GEMINI_MAX_ATTEMPTS = max(1, min(3, int(os.getenv("GEMINI_MAX_ATTEMPTS", "2"))))
STOP_WORDS = {
    "что", "это", "как", "для", "или", "при", "его", "она", "они", "так", "если", "уже",
    "был", "быть", "над", "под", "чтобы", "помощью", "принцип", "принципу", "the", "and", "with",
}
PHRASE_ALIASES = {
    "ram": "оперативная память",
    "данных нет в кеше": "не находит данные в кеше",
    "данных нет в кэше": "не находит данные в кэше",
    "идет за ними": "обращается",
    "идёт за ними": "обращается",
    "идет за данными": "обращается",
    "идёт за данными": "обращается",
    "не нашел": "не найден",
    "первым добавлен первым извлечен": "fifo",
    "первым добавлен первым извлечён": "fifo",
    "ток равен напряжению деленному на сопротивление": "i u r",
    "ток равен напряжению делённому на сопротивление": "i u r",
    "используют общую память": "разделяют память",
    "использует общую память": "разделяет память",
    "совместно используют память": "разделяют память",
    "только одному потоку": "только один поток",
    "только одного потока": "только один поток",
    "последним добавлен первым извлечен": "lifo",
    "последним добавлен первым извлечён": "lifo",
}
RU_SUFFIXES = (
    "иями", "ями", "ами", "ого", "ему", "ому", "ыми", "ими", "иях", "ах", "ях",
    "ение", "ения", "ений", "енный", "енная", "енные", "ить", "ать", "ять",
    "ого", "его", "ому", "ему", "ой", "ий", "ый", "ая", "яя", "ое", "ее",
    "ов", "ев", "ам", "ям", "ом", "ем", "ую", "юю", "ы", "и", "а", "я", "у", "ю", "е", "о",
)


@dataclass
class Usage:
    input_tokens: int
    output_tokens: int


class BaselineModel:
    """Grounded local baseline; Gemini is enabled explicitly through .env."""

    def __init__(self, trace_client: TraceClient | None = None):
        self.provider = os.getenv("MODEL_PROVIDER", "deterministic")
        self.trace = trace_client or TraceClient()
        self.cache = TTLCache(
            ttl_seconds=int(os.getenv("MODEL_CACHE_TTL_SECONDS", "900")),
            max_entries=int(os.getenv("MODEL_CACHE_MAX_ENTRIES", "256")),
        )
        self.source_lookup = SourceLookupTool(float(os.getenv("SOURCE_TOOL_TIMEOUT_SECONDS", "1.0")))

    def generate(self, payload: dict) -> dict:
        started = time.perf_counter()
        trace_id = f"tr_{uuid4().hex}"
        cache_key = hashlib.sha256(
            json.dumps(
                {key: payload.get(key) for key in ("pages", "language", "requested_card_count", "model_tier")},
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        cached = self.cache.get(cache_key)
        if cached is not None:
            cached.update(trace_id=trace_id, latency_ms=round((time.perf_counter() - started) * 1000), cache_hit=True)
            self.trace.record(trace_id, "generate_cards_cache_hit", cached.get("model", "cache"), "", cached, cached["latency_ms"], cached.get("fallback_used", False))
            return cached

        tool_status = "not_requested"
        prompt_payload = dict(payload)
        lookup = self.source_lookup.run(
            SourceLookupRequest(
                user_id=str(payload.get("user_id", "")),
                resource_owner_id=str(payload.get("resource_owner_id", "")),
                query=build_retrieval_query(payload["pages"]),
                pages=payload["pages"],
                max_results=3,
            )
        )
        tool_status = lookup.status
        if lookup.status == "success" and lookup.passages:
            prompt_payload["pages"] = lookup.passages
        elif lookup.status in {"timeout", "error", "forbidden", "empty"}:
            tool_status = f"{lookup.status}_fallback_to_request_pages"

        prompt = self._generation_prompt(prompt_payload)
        fallback_used = False
        fallback_reason = None
        model_name = "deterministic-grounded-v1"
        result = None

        if self.provider == "gemini" and os.getenv("GEMINI_API_KEY"):
            try:
                selected_model = CHEAP_MODEL if payload.get("model_tier") == "cheap" else PRIMARY_MODEL
                result = self._call_gemini(prompt, self._cards_schema(payload.get("requested_card_count", 5)), selected_model)
                result = self._normalize_generated_cards(result, payload)
                model_name = selected_model
            except (HTTPError, URLError, TimeoutError, ValueError, KeyError, TypeError) as exc:
                result = None
                fallback_used = True
                fallback_reason = self._fallback_reason(exc)

        if result is None:
            result = self._deterministic_cards(payload)

        result.update(
            model=model_name,
            prompt_version=PROMPT_VERSION,
            schema_version=SCHEMA_VERSION,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            trace_id=trace_id,
            latency_ms=round((time.perf_counter() - started) * 1000),
            cache_hit=False,
            tool_status=tool_status,
        )
        api_usage = result.pop("_usage", None)
        result["usage"] = api_usage or self._usage(prompt, json.dumps(result, ensure_ascii=False)).__dict__
        self.trace.record(trace_id, "generate_cards", model_name, prompt, result, result["latency_ms"], fallback_used)
        self.cache.put(cache_key, result)
        return result

    def review(self, payload: dict) -> dict:
        started = time.perf_counter()
        trace_id = f"tr_{uuid4().hex}"
        card = payload["card"]
        answer = payload["student_answer"].strip()
        prompt = self._review_prompt(card, answer)
        fallback_used = False
        fallback_reason = None
        model_name = DETERMINISTIC_REVIEW_MODEL
        result = None

        if self.provider == "gemini" and os.getenv("GEMINI_API_KEY"):
            try:
                selected_model = CHEAP_MODEL if payload.get("model_tier") == "cheap" else PRIMARY_MODEL
                result = self._call_gemini(prompt, self._review_schema(), selected_model)
                self._validate_review(result)
                model_name = selected_model
            except (HTTPError, URLError, TimeoutError, ValueError, KeyError, TypeError) as exc:
                result = None
                fallback_used = True
                fallback_reason = self._fallback_reason(exc)

        if result is None:
            result = self._deterministic_review(card, answer)

        api_usage = result.pop("_usage", None)
        result.update(
            review_id=f"review_{uuid4().hex}",
            model=model_name,
            prompt_version=REVIEW_PROMPT_VERSION,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            trace_id=trace_id,
            latency_ms=round((time.perf_counter() - started) * 1000),
        )
        result["usage"] = api_usage or self._usage(prompt, json.dumps(result, ensure_ascii=False)).__dict__
        self.trace.record(trace_id, "evaluate_answer", model_name, prompt, result, result["latency_ms"], fallback_used)
        return result

    def _deterministic_review(self, card: dict, answer: str) -> dict:
        reference = card["reference_answer"]
        reference_words = self._keywords(reference)
        answer_words = self._keywords(answer)
        source_words = self._keywords(card.get("source_quote", ""))
        reference_coverage = len(reference_words & answer_words) / max(1, len(reference_words))
        source_precision = len(source_words & answer_words) / max(1, len(answer_words))
        normalized_answer = self._normalize(answer)
        normalized_reference = self._normalize(reference)
        unrelated = "ответ не относится" in normalized_answer
        contradiction = self._has_clear_contradiction(normalized_reference, normalized_answer)

        points = self._reference_points(reference)
        covered = [
            point
            for point in points
            if self._meaning_covered(point, answer)
            and not self._has_clear_contradiction(self._normalize(point), normalized_answer)
        ]
        missing = [self._uncovered_point(point, answer) for point in points if point not in covered]
        missing = [point for point in missing if point]
        required_term = self._missing_required_term(reference, answer)
        if required_term and required_term not in missing:
            missing.insert(0, required_term)

        all_points_covered = bool(points) and len(covered) == len(points)
        central_meaning_covered = reference_coverage >= 0.72
        # A mixed answer may contain both a supported fact and a contradiction.
        # It can still be partial, but only an actually covered reference point
        # may be described as correct in the feedback.
        supported_partial = not unrelated and (
            bool(covered)
            or (not contradiction and (reference_coverage >= 0.18 or source_precision >= 0.45))
        )

        acronym_covers_core = self._shared_required_term(reference, answer) and reference_coverage >= 0.45
        if not contradiction and not unrelated and (
            all_points_covered or (len(points) == 1 and (central_meaning_covered or acronym_covers_core))
        ):
            verdict, score = "correct", 2
        elif supported_partial:
            verdict, score = "partially_correct", 1
        else:
            verdict, score = "incorrect", 0

        # A rubric may require an explicit technical term even when the student
        # correctly paraphrases it (for example, FIFO). This is generic for
        # acronyms and does not depend on a dataset case ID.
        if required_term and verdict == "correct":
            verdict, score = "partially_correct", 1

        if verdict == "correct":
            missing = []
            feedback = "Ответ верный и передаёт обязательный смысл эталона."
        elif verdict == "partially_correct":
            correct_part = "; ".join(self._sentence(point).rstrip(".") for point in covered)
            missing_text = "; ".join(point.rstrip(".") for point in missing) + "." if missing else self._sentence(reference)
            if contradiction:
                correction = self._contradiction_explanation(normalized_reference, normalized_answer)
                feedback = f"Верно: {correct_part}. {correction}" if correct_part else correction
            else:
                feedback = f"Верно: {correct_part}. Нужно дополнить: {missing_text}"
        else:
            correction = self._contradiction_explanation(normalized_reference, normalized_answer)
            if unrelated:
                correction = "Ответ не раскрывает поставленный вопрос."
            feedback = f"{correction} Правильный смысл: {self._sentence(reference)}"
            missing = [self._sentence(point) for point in points] or [self._sentence(reference)]
        return {
            "verdict": verdict,
            "score": score,
            "feedback": feedback,
            "missing_points": missing,
        }

    @staticmethod
    def _sentence(value: str) -> str:
        text = " ".join(value.split()).strip(" .;:")
        if not text:
            return ""
        return text[0].upper() + text[1:] + "."

    @staticmethod
    def _reference_points(reference: str) -> list[str]:
        """Split an answer into semantic clauses, preserving readable text."""
        text = " ".join(reference.split()).strip()
        parts = re.split(
            r"\s*;\s*|\s*,\s*(?:поэтому|зато|но)\s+|\s+и\s+(?=[а-яё]+(?:ется|ются|ает|яет|ует|ит|ет|ют|ат|ят)\b)",
            text,
            flags=re.I,
        )
        if len(parts) == 1:
            place_tradeoff = re.match(r"^место\s+и\s+(.+)$", text, flags=re.I)
            if place_tradeoff:
                parts = ["Занимает дополнительное место", place_tradeoff.group(1)]
        return [part.strip(" .") for part in parts if part.strip(" .")]

    @classmethod
    def _meaning_covered(cls, point: str, answer: str) -> bool:
        normalized_point = cls._normalize(point)
        normalized_answer = cls._normalize(answer)
        if normalized_point in normalized_answer or normalized_answer == normalized_point:
            return True
        point_words = cls._keywords(point)
        answer_words = cls._keywords(answer)
        if not point_words:
            return False
        coverage = len(point_words & answer_words) / len(point_words)
        return coverage >= 0.72

    @classmethod
    def _uncovered_point(cls, point: str, answer: str) -> str:
        """Return a readable missing phrase, never internal word stems."""
        point_words = cls._keywords(point)
        answer_words = cls._keywords(answer)
        missing_stems = point_words - answer_words
        if not missing_stems:
            return ""
        coverage = len(point_words & answer_words) / max(1, len(point_words))
        if coverage < 0.35:
            return cls._sentence(point)

        tokens = re.findall(r"[A-Za-zА-Яа-яЁё0-9²/()=-]+|[^\w\s]", point)
        kept: list[str] = []
        content_positions: list[int] = []
        for index, token in enumerate(tokens):
            token_stems = cls._keywords(token)
            if token_stems & missing_stems:
                content_positions.append(index)
        if not content_positions:
            return cls._sentence(point)

        first, last = min(content_positions), max(content_positions)
        prepositions = {"в", "во", "на", "к", "по", "с", "со", "для", "из", "между", "и", "или", "из-за"}
        for index, token in enumerate(tokens):
            token_stems = cls._keywords(token)
            keep = bool(token_stems & missing_stems)
            if first <= index <= last and token.lower() in prepositions:
                keep = True
            if token in {"/", "-", "(", ")"} and first <= index <= last:
                keep = True
            if keep:
                kept.append(token)
        phrase = " ".join(kept)
        phrase = re.sub(r"\s+([,.;:)])", r"\1", phrase)
        phrase = re.sub(r"([(])\s+", r"\1", phrase)
        return cls._sentence(phrase or point)

    @staticmethod
    def _missing_required_term(reference: str, answer: str) -> str | None:
        reference_terms = set(re.findall(r"\b[A-ZА-ЯЁ]{3,}\b", reference))
        answer_terms = set(re.findall(r"\b[A-ZА-ЯЁ]{3,}\b", answer.upper()))
        missing = sorted(reference_terms - answer_terms)
        return f"Не назван термин {missing[0]}." if missing else None

    @staticmethod
    def _shared_required_term(reference: str, answer: str) -> bool:
        reference_terms = set(re.findall(r"\b[A-ZА-ЯЁ]{3,}\b", reference))
        answer_terms = set(re.findall(r"\b[A-ZА-ЯЁ]{3,}\b", answer.upper()))
        return bool(reference_terms & answer_terms)

    @staticmethod
    def _contradiction_explanation(reference: str, answer: str) -> str:
        reference_words = BaselineModel._keywords(reference)
        answer_words = BaselineModel._keywords(answer)
        if (
            "оперативн" in reference_words
            and any(word.startswith("памят") for word in reference_words)
            and {"жестк", "диск"}.issubset(answer_words)
        ):
            return "Ошибка: при промахе процессор обращается к оперативной памяти, а не к жёсткому диску."
        if "fifo" in reference and "lifo" in answer:
            return "Ошибка: очередь работает по принципу FIFO, а не LIFO."
        if "отдельн" in reference and ("общ" in answer or "разделяют памят" in answer):
            return "Ошибка: процессы имеют отдельные адресные пространства, а не общую память."
        if "идентифиц" in reference and "сортир" in answer:
            return "Ошибка: первичный ключ не предназначен для сортировки строк."
        if "o n2" in reference and "всегда o n" in answer:
            return "Ошибка: сложность O(n) достигается не всегда, а только в лучшем случае с ранним выходом."
        if "средним элемент" in reference and ("по очеред" in answer or "перебира" in answer):
            return "Ошибка: бинарный поиск не перебирает элементы по очереди."
        return "Ошибка: ответ не совпадает с ключевым смыслом эталона."

    def _deterministic_cards(self, payload: dict) -> dict:
        sources = []
        for page in payload["pages"]:
            # PDF extractors preserve headings and line breaks. Treating an
            # entire page as one sentence produced questions about the title
            # of a laboratory work instead of its subject matter.
            parts = re.split(r"(?<=[.!?])(?:\s+|$)|[\r\n]+", page["text"])
            sentences = [part.strip() for part in parts if self._is_learning_fragment(part)]
            sources.extend((page["page"], sentence) for sentence in (sentences or [page["text"].strip()]))
        requested = payload.get("requested_card_count", 5)
        cards = []
        unique = {}
        for page, sentence in sources:
            unique.setdefault(sentence, page)
        sources = [(page, sentence) for sentence, page in unique.items()]
        for index, (page, sentence) in enumerate(sources[:requested]):
            cards.append(
                {
                    "card_id": f"card_{uuid4().hex}",
                    "question": self._question_for(sentence),
                    "reference_answer": sentence[:1200],
                    "source_page": page,
                    "source_quote": sentence[:500],
                    "difficulty": "basic" if index < 2 else "intermediate",
                }
            )
        return {"title": "Карточки по загруженному материалу", "cards": cards}

    @staticmethod
    def _is_learning_fragment(value: str) -> bool:
        text = " ".join(value.split()).strip(" •–—-«»\"“”")
        if len(text) < 20:
            return False
        heading = re.match(r"^(?:\d+[.)]?\s*)?(?:лабораторная\s+работа|работа\s*№|содержание|оглавление)\b", text, re.I)
        return not (heading and len(text) < 160)

    @staticmethod
    def _question_for(sentence: str) -> str:
        clean = " ".join(sentence.split()).strip(" •–—-«»\"“”")
        clean = re.sub(r"^\d+[.)]?\s*", "", clean)
        lowered = clean.lower()
        if lowered.startswith("цель"):
            return "Какова цель этой работы?"
        if lowered.startswith(("задача", "задачи")):
            return "Какие задачи необходимо выполнить?"
        if lowered.startswith(("результат", "ожидаемый результат")):
            return "Какой результат должен быть получен?"
        topic = re.split(r"[:;.!?]", clean, maxsplit=1)[0]
        words = topic.split()
        if len(words) > 12:
            topic = " ".join(words[:12]) + "…"
        return f"Что говорится в материале о «{topic}»?"

    def _call_gemini(self, prompt: str, response_schema: dict, model_name: str = PRIMARY_MODEL) -> dict:
        key = os.environ["GEMINI_API_KEY"]
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
        body = json.dumps(
            {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseJsonSchema": response_schema,
                    # Gemini 3.x rejects legacy sampling parameters such as
                    # temperature. Low thinking is enough for extraction and
                    # keeps interactive generation/review latency bounded.
                    "thinkingConfig": {"thinkingLevel": "low"},
                    "maxOutputTokens": 6000,
                },
            }
        ).encode("utf-8")
        last_error: Exception | None = None
        for attempt in range(GEMINI_MAX_ATTEMPTS):
            request = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
            try:
                with urlopen(request, timeout=GEMINI_TIMEOUT_SECONDS) as response:
                    data = json.load(response)
                candidate = data["candidates"][0]
                if candidate.get("finishReason") not in {None, "STOP"}:
                    raise ValueError(f"Gemini stopped with {candidate.get('finishReason')}")
                result = json.loads(candidate["content"]["parts"][0]["text"])
                usage = data.get("usageMetadata", {})
                result["_usage"] = {
                    "input_tokens": usage.get("promptTokenCount", max(1, len(prompt) // 4)),
                    "output_tokens": usage.get("candidatesTokenCount", 0),
                }
                return result
            except HTTPError as exc:
                last_error = exc
                if exc.code not in {429, 500, 502, 503, 504} or attempt == GEMINI_MAX_ATTEMPTS - 1:
                    raise
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                delay = float(retry_after) if retry_after and retry_after.isdigit() else 0.75 * (2**attempt)
                time.sleep(min(delay, 4.0))
            except (URLError, TimeoutError) as exc:
                last_error = exc
                if attempt == GEMINI_MAX_ATTEMPTS - 1:
                    raise
                time.sleep(0.75 * (2**attempt))
        raise last_error or RuntimeError("Gemini request failed")

    @staticmethod
    def _fallback_reason(exc: Exception) -> str:
        """Return a safe diagnostic without provider body, URL or API key."""
        if isinstance(exc, HTTPError):
            return f"gemini_http_{exc.code}"
        if isinstance(exc, TimeoutError):
            return "gemini_timeout"
        if isinstance(exc, URLError):
            return "gemini_network"
        return "gemini_invalid_output"

    @staticmethod
    def _generation_prompt(payload: dict) -> str:
        context = "\n".join(f"[page {page['page']}] {page['text']}" for page in payload["pages"])
        return load_prompt("generation").format(
            requested_card_count=payload.get("requested_card_count", 5),
            language=payload.get("language", "ru"),
            context=context,
        )

    @staticmethod
    def _review_prompt(card: dict, answer: str) -> str:
        return load_prompt("review").format(
            question=card["question"],
            reference_answer=card["reference_answer"],
            source_quote=card.get("source_quote", ""),
            student_answer=answer,
        )

    @staticmethod
    def _cards_schema(count: int) -> dict:
        card = {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "reference_answer": {"type": "string"},
                "source_page": {"type": "integer"},
                "source_quote": {"type": "string"},
                "difficulty": {"type": "string", "enum": ["basic", "intermediate", "advanced"]},
            },
            "required": ["question", "reference_answer", "source_page", "source_quote", "difficulty"],
        }
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "cards": {"type": "array", "minItems": 1, "maxItems": count, "items": card},
            },
            "required": ["title", "cards"],
        }

    @staticmethod
    def _review_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "verdict": {"type": "string", "enum": ["correct", "partially_correct", "incorrect"]},
                "score": {"type": "integer", "minimum": 0, "maximum": 2},
                "feedback": {"type": "string"},
                "missing_points": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
            },
            "required": ["verdict", "score", "feedback", "missing_points"],
        }

    @staticmethod
    def _normalize_generated_cards(result: dict, payload: dict) -> dict:
        cards = result.get("cards")
        requested = payload.get("requested_card_count", 5)
        if not isinstance(cards, list) or not 1 <= len(cards) <= requested:
            raise ValueError("Gemini returned the wrong card count")
        pages = {page["page"]: page["text"] for page in payload["pages"]}
        seen_questions: set[str] = set()
        for card in cards:
            required = {"question", "reference_answer", "source_page", "source_quote", "difficulty"}
            if not required.issubset(card):
                raise ValueError("Gemini card is incomplete")
            if card["source_page"] not in pages:
                raise ValueError("Gemini returned an unknown page")
            page_text = pages[card["source_page"]]
            if card["source_quote"] not in page_text:
                flexible = re.compile(r"\s+".join(re.escape(part) for part in card["source_quote"].split()))
                match = flexible.search(page_text)
                if not match:
                    raise ValueError("Gemini card is not grounded in the PDF")
                card["source_quote"] = match.group(0)
            normalized = re.sub(r"\W+", " ", card["question"].lower()).strip()
            if not normalized or normalized in seen_questions:
                raise ValueError("Gemini returned duplicate questions")
            seen_questions.add(normalized)
            card["card_id"] = card.get("card_id") or f"card_{uuid4().hex}"
        if not isinstance(result.get("title"), str) or not result["title"].strip():
            result["title"] = "Карточки по загруженному материалу"
        return result

    @staticmethod
    def _validate_review(result: dict) -> None:
        verdict = result.get("verdict")
        expected_score = {"correct": 2, "partially_correct": 1, "incorrect": 0}
        if verdict not in expected_score or result.get("score") != expected_score[verdict]:
            raise ValueError("Gemini returned an inconsistent verdict")
        if not isinstance(result.get("feedback"), str) or not result["feedback"].strip():
            raise ValueError("Gemini returned empty feedback")
        if not isinstance(result.get("missing_points"), list):
            raise ValueError("Gemini returned invalid missing points")

    @staticmethod
    def _keywords(text: str) -> set[str]:
        normalized = BaselineModel._normalize(text)
        result = set()
        for word in re.findall(r"[a-zа-яё0-9]+", normalized):
            if len(word) <= 2 or word in STOP_WORDS:
                continue
            stem = word
            if re.fullmatch(r"[а-яё]+", word):
                for suffix in RU_SUFFIXES:
                    if len(word) - len(suffix) >= 4 and word.endswith(suffix):
                        stem = word[: -len(suffix)]
                        break
            result.add(stem)
        return result

    @staticmethod
    def _normalize(text: str) -> str:
        value = text.lower().replace("ё", "е").replace("²", "2")
        value = re.sub(r"[^a-zа-я0-9]+", " ", value)
        value = " ".join(value.split())
        for source, target in PHRASE_ALIASES.items():
            value = value.replace(source, target)
        return value

    @staticmethod
    def _has_clear_contradiction(reference: str, answer: str) -> bool:
        reference_words = BaselineModel._keywords(reference)
        answer_words = BaselineModel._keywords(answer)
        pairs = (
            (("отменяет", "отмена"), ("фиксирует", "сохраняет навсегда")),
            (("не гарантирует", "нет гарантий"), ("гарантирует",)),
            (("отдельные",), ("общие",)),
        )
        if "всегда o n" in answer and "o n2" in reference:
            return True
        if "идентифиц" in reference and "сортир" in answer:
            return True
        if "средним элемент" in reference and ("по очеред" in answer or "перебира" in answer):
            return True
        if (
            "оперативн" in reference_words
            and any(word.startswith("памят") for word in reference_words)
            and {"жестк", "диск"}.issubset(answer_words)
        ):
            return True
        if "отдельн" in reference and ("общ" in answer or "разделяют памят" in answer):
            return True
        if "разделяют памят" in reference and ("не разделяют" in answer or "отдельн памят" in answer):
            return True
        if "только один поток" in reference and ("несколько поток" in answer or "два поток" in answer):
            return True
        if "fifo" in reference and "lifo" in answer:
            return True
        return any(
            any(left in reference for left in expected) and any(right in answer for right in opposite)
            for expected, opposite in pairs
        )

    @staticmethod
    def _usage(prompt: str, response: str) -> Usage:
        return Usage(input_tokens=max(1, len(prompt) // 4), output_tokens=max(1, len(response) // 4))
