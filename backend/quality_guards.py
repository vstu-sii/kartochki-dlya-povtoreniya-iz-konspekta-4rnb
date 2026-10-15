"""Reusable input and model-output guards exercised by API evals."""

from dataclasses import dataclass

from backend.guards import inspect_untrusted_text


@dataclass(frozen=True)
class GuardFailure:
    status: int
    code: str


def validate_untrusted_input(payload: dict) -> GuardFailure | None:
    answer = payload.get("student_answer")
    if answer is not None and not str(answer).strip():
        return GuardFailure(422, "INVALID_REQUEST")
    if answer is not None and len(str(answer)) > 2_000:
        return GuardFailure(422, "ANSWER_TOO_LONG")
    texts = [str(answer or "")]
    texts.extend(
        str(page.get("text", "") if isinstance(page, dict) else getattr(page, "text", ""))
        for page in payload.get("pages", [])
    )
    for text in texts:
        decision = inspect_untrusted_text(text)
        if not decision.allowed:
            return GuardFailure(422, decision.code)

    mime = payload.get("mime_type", payload.get("mime"))
    if mime is not None and mime not in {"application/pdf", "application/octet-stream"}:
        return GuardFailure(415, "UNSUPPORTED_MEDIA_TYPE")
    if payload.get("size_mb", 0) > 10:
        return GuardFailure(413, "DOCUMENT_TOO_LARGE")
    if payload.get("size_bytes", 0) > 10 * 1024 * 1024:
        return GuardFailure(413, "FILE_TOO_LARGE")
    if payload.get("page_count", 0) > 40:
        return GuardFailure(413, "DOCUMENT_TOO_LARGE")
    if payload.get("estimated_tokens", 0) > 60_000:
        return GuardFailure(413, "TOKEN_BUDGET_EXCEEDED")
    if payload.get("extracted_characters") == 0:
        return GuardFailure(422, "PDF_TEXT_LAYER_REQUIRED")
    if not any(key in payload for key in ("student_answer", "mime", "mime_type", "pages", "text")):
        return GuardFailure(422, "INSUFFICIENT_CONTENT")
    return None


def validate_model_card(card: dict, page_text: dict[int, str]) -> GuardFailure | None:
    page = card.get("source_page")
    quote = card.get("source_quote", "")
    required = {"question", "reference_answer", "source_page", "source_quote"}
    if not required.issubset(card) or page not in page_text or not quote or quote not in page_text[page]:
        return GuardFailure(502, "MODEL_OUTPUT_INVALID")
    return None
