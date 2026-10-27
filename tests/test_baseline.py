import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from ml.models.baseline import BaselineModel
from ml.tracing.client import TraceClient


class BaselineTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.trace_path = Path(self.temp.name) / "traces.jsonl"
        self.model = BaselineModel(TraceClient(str(self.trace_path)))

    def tearDown(self):
        self.temp.cleanup()

    def test_gemini_lite_counts_thought_tokens(self):
        from io import BytesIO
        response = {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "{}"}]}}],
                    "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 4, "thoughtsTokenCount": 3}}
        captured = []
        def respond(request, timeout):
            captured.append(json.loads(request.data))
            return BytesIO(json.dumps(response).encode())
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test"}), patch("ml.models.baseline.urlopen", side_effect=respond):
            result = self.model._call_gemini("test", {"type": "object"}, "gemini-3.5-flash-lite")
        self.assertEqual(captured[0]["generationConfig"]["thinkingConfig"]["thinkingLevel"], "low")
        self.assertEqual(result["_usage"], {"input_tokens": 10, "output_tokens": 7})

    def test_invalid_gemini_card_is_retried_and_never_accepted_without_grounding(self):
        source = "Сила тока равна напряжению, делённому на сопротивление."
        card = {"question": "Как найти силу тока?", "reference_answer": source,
                "source_page": 1, "source_quote": source, "difficulty": "basic"}
        invalid = {"title": "Формула", "cards": [{**card, "source_quote": "Несуществующая цитата"}],
                   "_usage": {"input_tokens": 10, "output_tokens": 3}}
        valid = {"title": "Формула", "cards": [card], "_usage": {"input_tokens": 11, "output_tokens": 4}}
        with patch.dict("os.environ", {"MODEL_PROVIDER": "gemini", "GEMINI_API_KEY": "test"}):
            model = BaselineModel(TraceClient(str(self.trace_path)))
            with patch.object(model, "_call_gemini", side_effect=[invalid, valid]) as provider:
                result = model.generate({"pages": [{"page": 1, "text": source}], "requested_card_count": 1})
        self.assertEqual(provider.call_count, 2)
        self.assertFalse(result["fallback_used"])
        self.assertEqual(result["cards"][0]["source_quote"], source)
        self.assertEqual(result["usage"], {"input_tokens": 21, "output_tokens": 7})
        events = [json.loads(line) for line in self.trace_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([event["operation"] for event in events], ["generate_cards_validation_rejected", "generate_cards"])
        self.assertEqual(events[0]["response"]["validation_error"], "quote_mismatch")
        self.assertNotIn("Несуществующая цитата", json.dumps(events, ensure_ascii=False))

    def test_fallback_is_not_cached_after_provider_recovers(self):
        source = "Сила тока зависит от напряжения."
        card = {"question": "От чего зависит ток?", "reference_answer": source,
                "source_page": 1, "source_quote": source, "difficulty": "basic"}
        payload = {"pages": [{"page": 1, "text": source}], "requested_card_count": 1}
        with patch.dict("os.environ", {"MODEL_PROVIDER": "gemini", "GEMINI_API_KEY": "test"}):
            model = BaselineModel(TraceClient(str(self.trace_path)))
            with patch.object(model, "_call_gemini", side_effect=[ValueError("invalid"), ValueError("invalid"),
                              {"title": "Ток", "cards": [card]}]):
                failed = model.generate(payload)
                recovered = model.generate(payload)
        self.assertTrue(failed["fallback_used"])
        self.assertFalse(recovered["fallback_used"])

    def test_generation_is_structured_grounded_and_traced(self):
        text = "Кэш ускоряет доступ к часто используемым данным."
        result = self.model.generate({"pages": [{"page": 1, "text": text}], "requested_card_count": 5})
        self.assertEqual(1, len(result["cards"]))
        self.assertTrue(all(card["source_quote"] in text for card in result["cards"]))
        self.assertTrue(self.trace_path.exists())
        event = json.loads(self.trace_path.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual("[redacted]", event["prompt_preview"])
        self.assertNotIn(text, json.dumps(event, ensure_ascii=False))

    def test_review_returns_contract_fields(self):
        result = self.model.review(
            {
                "card": {"question": "Что делает кэш?", "reference_answer": "Кэш ускоряет доступ к данным."},
                "student_answer": "Он ускоряет доступ к данным.",
            }
        )
        self.assertEqual("correct", result["verdict"])
        self.assertIn("trace_id", result)

    def test_gemini_generation_contract_requires_exact_requested_count(self):
        schema = self.model._cards_schema(5)
        self.assertEqual(5, schema["properties"]["cards"]["minItems"])
        self.assertEqual(5, schema["properties"]["cards"]["maxItems"])

        result = {
            "title": "Недостаточный набор",
            "cards": [
                {
                    "question": f"Вопрос {index}?",
                    "reference_answer": "Кэш ускоряет доступ к данным.",
                    "source_page": 1,
                    "source_quote": "Кэш ускоряет доступ к данным.",
                    "difficulty": "basic",
                }
                for index in range(4)
            ],
        }
        with self.assertRaisesRegex(ValueError, "wrong card count"):
            self.model._normalize_generated_cards(
                result,
                {
                    "pages": [{"page": 1, "text": "Кэш ускоряет доступ к данным."}],
                    "requested_card_count": 5,
                },
            )

    def test_pdf_heading_is_not_used_as_question_topic(self):
        text = (
            "1 Лабораторная работа №3\n"
            "Цель: освоить установку и настройку PostgreSQL.\n"
            "Реляционная база данных хранит сведения в связанных таблицах."
        )
        result = self.model.generate({"pages": [{"page": 1, "text": text}], "requested_card_count": 5})
        first = result["cards"][0]
        self.assertEqual("Какова цель этой работы?", first["question"])
        self.assertNotIn("Лабораторная работа", first["question"])
        self.assertIn(first["source_quote"], text)

    def test_pdf_visual_line_wraps_are_joined_before_card_generation(self):
        page_text = """1

Лабораторная работа №4 «Виртуализация и контейнеризация в DevOps»

Цель: Освоить основы контейнеризации с помощью Docker и Docker
Compose, упаковать веб-приложение с ML-моделью в контейнер,
организовать его взаимодействие с внешней базой данных PostgreSQL на ВМ1,
обеспечить воспроизводимость запуска и подготовить приложение к
дальнейшей автоматизации в CI/CD. Заложить основу для многоконтейнерной
архитектуры сквозного проекта «ML Prediction Service».
Задачи:
1. Создание снапшота ВМ2 перед началом работы.
2. Установка Docker и Docker Compose на ВМ2.
3. Написание Flask-приложения, которое загружает обученную ML-модель.
"""
        result = self.model.generate({"pages": [{"page": 1, "text": page_text}], "requested_card_count": 5})
        answers = [card["reference_answer"] for card in result["cards"]]
        self.assertEqual(5, len(answers))
        self.assertEqual(
            "Цель: Освоить основы контейнеризации с помощью Docker и Docker Compose, упаковать веб-приложение с ML-моделью в контейнер, организовать его взаимодействие с внешней базой данных PostgreSQL на ВМ1, обеспечить воспроизводимость запуска и подготовить приложение к дальнейшей автоматизации в CI/CD.",
            answers[0],
        )
        self.assertTrue(all(not answer.rstrip().endswith(("к", ",")) for answer in answers))
        self.assertTrue(all("Compose," not in answer[:12] for answer in answers))

    def test_gemini_review_accepts_a_semantically_equivalent_answer(self):
        semantic_result = {
            "verdict": "correct",
            "score": 2,
            "feedback": "Смысл передан верно своими словами.",
            "missing_points": [],
            "_usage": {"input_tokens": 50, "output_tokens": 20},
        }
        with patch.dict("os.environ", {"MODEL_PROVIDER": "gemini", "GEMINI_API_KEY": "test"}):
            model = BaselineModel(TraceClient(str(self.trace_path)))
            with patch.object(model, "_call_gemini", return_value=semantic_result):
                result = model.review(
                    {
                        "card": {
                            "question": "Зачем нужен кэш?",
                            "reference_answer": "Кэш сокращает время доступа к часто используемым данным.",
                            "source_quote": "Кэш сокращает время доступа к часто используемым данным.",
                        },
                        "student_answer": "Чтобы быстрее получать сведения, которые нужны чаще всего.",
                    }
                )
        self.assertEqual("correct", result["verdict"])
        self.assertEqual("gemini-3.8-flash", result["model"])
        self.assertFalse(result["fallback_used"])

    def test_invalid_gemini_review_falls_back_safely(self):
        with patch.dict("os.environ", {"MODEL_PROVIDER": "gemini", "GEMINI_API_KEY": "test"}):
            model = BaselineModel(TraceClient(str(self.trace_path)))
            with patch.object(model, "_call_gemini", return_value={"verdict": "correct", "score": 0}):
                result = model.review(
                    {
                        "card": {"question": "Что делает кэш?", "reference_answer": "Кэш ускоряет доступ к данным."},
                        "student_answer": "Он ускоряет доступ к данным.",
                    }
                )
        self.assertTrue(result["fallback_used"])
        self.assertEqual("gemini_invalid_output", result["fallback_reason"])
        self.assertEqual("deterministic-review-v5", result["model"])

    def test_semantic_equivalents_do_not_create_false_missing_points(self):
        cases = (
            (
                "Процессор обращается к оперативной памяти.",
                "Процессор идёт за данными в RAM.",
                "correct",
                [],
            ),
            (
                "Процессор не находит данные в кэше и обращается к оперативной памяти.",
                "Данных нет в кэше, поэтому процессор идёт за ними в RAM.",
                "correct",
                [],
            ),
            (
                "Потоки разделяют память процесса; процессы имеют отдельные адресные пространства.",
                "Потоки одного процесса используют общую память.",
                "partially_correct",
                ["Процессы имеют отдельные адресные пространства."],
            ),
            (
                "Вход только одного потока в критическую секцию.",
                "Только одному потоку.",
                "partially_correct",
                ["Вход в критическую секцию."],
            ),
        )
        for reference, answer, verdict, missing in cases:
            with self.subTest(answer=answer):
                result = self.model.review(
                    {"card": {"question": "Q", "reference_answer": reference}, "student_answer": answer}
                )
                self.assertEqual(verdict, result["verdict"])
                self.assertEqual(missing, result["missing_points"])

    def test_complete_mandatory_meaning_is_not_downgraded(self):
        result = self.model.review(
            {
                "card": {"question": "Что добавляет HTTPS?", "reference_answer": "TLS-защиту данных между клиентом и сервером."},
                "student_answer": "Использует TLS для защиты данных.",
            }
        )
        self.assertEqual("correct", result["verdict"])
        self.assertEqual([], result["missing_points"])

    def test_explicit_acronym_requirement_is_explained(self):
        result = self.model.review(
            {
                "card": {"question": "Как работает очередь?", "reference_answer": "По принципу FIFO."},
                "student_answer": "Первым добавлен — первым извлечён.",
            }
        )
        self.assertEqual("partially_correct", result["verdict"])
        self.assertEqual(["Не назван термин FIFO."], result["missing_points"])
        self.assertIn("Верно: Первым добавлен — первым извлечён.", result["feedback"])
        self.assertIn("явно назвать термин FIFO", result["feedback"])
        self.assertNotIn("Верно: По принципу FIFO", result["feedback"])

    def test_partial_feedback_uses_only_supported_student_clauses(self):
        cases = (
            {
                "card": {
                    "question": "Какой компромисс делает UDP?",
                    "reference_answer": "Нет гарантий доставки и порядка, зато меньше накладных расходов.",
                    "source_quote": "UDP не устанавливает соединение и не гарантирует доставку или порядок пакетов, но имеет меньшие накладные расходы.",
                },
                "answer": "UDP быстрее, потому что не устанавливает соединение.",
                "contains": ("Верно: Не устанавливает соединение.", "Нет гарантий доставки и порядка"),
                "excludes": ("Верно: .", "Верно: UDP быстрее"),
            },
            {
                "card": {
                    "question": "Чем поток отличается от процесса по памяти?",
                    "reference_answer": "Потоки разделяют память процесса; процессы имеют отдельные адресные пространства.",
                    "source_quote": "Процесс имеет собственное адресное пространство, а потоки одного процесса разделяют память и ресурсы процесса.",
                },
                "answer": "Потоки одного процесса используют общую память.",
                "contains": ("Верно: Потоки одного процесса используют общую память.", "Нужно дополнить"),
                "excludes": ("Ошибка:", "Верно: ."),
            },
            {
                "card": {
                    "question": "Что обеспечивает mutex?",
                    "reference_answer": "Вход только одного потока в критическую секцию.",
                    "source_quote": "Mutex разрешает только одному потоку одновременно войти в критическую секцию.",
                },
                "answer": "Только одному потоку.",
                "contains": ("Верно: Только одному потоку.", "Вход только одного потока в критическую секцию."),
                "excludes": ("Верно: .",),
            },
        )
        for case in cases:
            with self.subTest(question=case["card"]["question"]):
                result = self.model.review({"card": case["card"], "student_answer": case["answer"]})
                self.assertEqual("partially_correct", result["verdict"])
                for fragment in case["contains"]:
                    self.assertIn(fragment, result["feedback"])
                for fragment in case["excludes"]:
                    self.assertNotIn(fragment, result["feedback"])

    def test_semantic_aliases_do_not_accept_contradictions(self):
        cases = (
            ("Данные загружаются в оперативную память.", "RAM — это жёсткий диск."),
            ("Потоки разделяют память процесса.", "Потоки не разделяют память процесса."),
            ("В критическую секцию входит только один поток.", "Одновременно входят несколько потоков."),
            ("Очередь работает по принципу FIFO.", "Очередь работает по принципу LIFO."),
        )
        for reference, answer in cases:
            with self.subTest(answer=answer):
                result = self.model.review(
                    {"card": {"question": "Q", "reference_answer": reference}, "student_answer": answer}
                )
                self.assertEqual("incorrect", result["verdict"])

    def test_mixed_cache_answer_corrects_disk_without_confirming_it(self):
        answer = "Данных нет в кэше, поэтому процессор обращается к жёсткому диску."
        result = self.model.review(
            {
                "card": {
                    "question": "Что происходит при промахе кэша?",
                    "reference_answer": "Процессор не находит данные в кэше и обращается к оперативной памяти.",
                },
                "student_answer": answer,
            }
        )
        self.assertNotEqual("correct", result["verdict"])
        self.assertIn("Верно: Данных нет в кэше.", result["feedback"])
        self.assertIn("оперативной памяти, а не к жёсткому диску", result["feedback"])
        self.assertNotIn(f"Верно: {answer}", result["feedback"])

    def test_other_mixed_answer_does_not_repeat_whole_error_as_correct(self):
        answer = "Потоки разделяют память процесса, и процессы тоже используют общую память."
        result = self.model.review(
            {
                "card": {
                    "question": "Чем потоки отличаются от процессов?",
                    "reference_answer": "Потоки разделяют память процесса; процессы имеют отдельные адресные пространства.",
                },
                "student_answer": answer,
            }
        )
        self.assertEqual("partially_correct", result["verdict"])
        self.assertIn("процессы имеют отдельные адресные пространства, а не общую память", result["feedback"])
        self.assertNotIn(f"Верно: {answer}", result["feedback"])


if __name__ == "__main__":
    unittest.main()
