"""Public AI endpoints: validate, call the model service, then persist results."""

import asyncio
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import session_scope
from backend.limits import budget_limiter
from backend.models import AnswerReview, Card, CardRating, CardRatingEvent, CardSet, Document, StudySession
from backend.observability import record_budget
from backend.pdf_extractor import PdfExtractionError, extract_pdf_pages
from backend.quality_guards import validate_model_card, validate_untrusted_input


router = APIRouter(prefix="/v1/ai", tags=["AI"])
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai-service:8001")
AI_TIMEOUT_SECONDS = max(1.0, min(120.0, float(os.getenv("AI_TIMEOUT_SECONDS", "65"))))
AI_MAX_ATTEMPTS = max(1, min(3, int(os.getenv("AI_MAX_ATTEMPTS", "2"))))


class Page(BaseModel):
    page: int = Field(ge=1)
    text: str = Field(min_length=10, max_length=200_000)


class GenerateRequest(BaseModel):
    document_id: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    language: str = Field(default="ru", pattern=r"^(ru|en)$")
    pages: list[Page] = Field(min_length=1, max_length=40)
    requested_card_count: int = Field(default=5, ge=5, le=10)


class CardPayload(BaseModel):
    card_id: str
    question: str
    reference_answer: str
    source_page: int
    source_quote: str
    difficulty: str = "basic"


class ReviewRequest(BaseModel):
    session_id: str = Field(min_length=8, max_length=64)
    card: CardPayload
    student_answer: str = Field(min_length=1, max_length=2_000)


class SessionRequest(BaseModel):
    card_set_id: str = Field(min_length=8, max_length=64)
    user_id: str = Field(min_length=1, max_length=64)


class ProgressRequest(BaseModel):
    current_position: int = Field(ge=0)


class RatingRequest(BaseModel):
    value: str = Field(pattern=r"^(useful|not_useful|off_topic)$")


class CompleteRequest(BaseModel):
    answers: list[dict] = Field(default_factory=list, max_length=100)


def is_retryable_model_status(status_code: int) -> bool:
    """Retry only throttling and transient provider failures, never client errors."""
    return status_code == 429 or status_code >= 500


def ensure_session_access(study_session: StudySession | None, user_id: str | None = None) -> StudySession:
    if not study_session:
        raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND"})
    if not user_id:
        raise HTTPException(status_code=401, detail={"code": "USER_ID_REQUIRED"})
    if study_session.user_id != user_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN"})
    updated = study_session.updated_at
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    if updated < datetime.now(timezone.utc) - timedelta(days=30):
        raise HTTPException(status_code=410, detail={"code": "SESSION_EXPIRED"})
    return study_session


async def call_model(path: str, payload: dict) -> dict:
    if AI_SERVICE_URL == "inprocess":
        from ml.models.baseline import BaselineModel

        model = BaselineModel()
        return model.generate(payload) if path.endswith("card-sets") else model.review(payload)

    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=AI_TIMEOUT_SECONDS) as client:
        for attempt in range(1, AI_MAX_ATTEMPTS + 1):
            try:
                response = await client.post(f"{AI_SERVICE_URL}{path}", json=payload)
                response.raise_for_status()
                return response.json()
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
            except httpx.HTTPStatusError as exc:
                if not is_retryable_model_status(exc.response.status_code):
                    detail = exc.response.json() if exc.response.headers.get("content-type", "").startswith("application/json") else exc.response.text
                    raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc
                last_error = exc
            if attempt < AI_MAX_ATTEMPTS:
                await asyncio.sleep(0.1 * attempt)
    raise HTTPException(status_code=503, detail={"code": "AI_PROVIDER_UNAVAILABLE", "attempts": AI_MAX_ATTEMPTS}) from last_error


async def model_generation_version() -> str:
    """Read the generation prompt version from the service that owns it."""
    if AI_SERVICE_URL == "inprocess":
        from ml.models.baseline import PROMPT_VERSION

        return PROMPT_VERSION
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{AI_SERVICE_URL}/v1/model/metadata")
            response.raise_for_status()
            version = response.json()["prompt_versions"]["generation"]
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail={"code": "AI_METADATA_UNAVAILABLE"}) from exc
    if not isinstance(version, str) or not version:
        raise HTTPException(status_code=503, detail={"code": "AI_METADATA_UNAVAILABLE"})
    return version


def idempotency_identity(user_id: str, operation: str, client_key: str, prompt_version: str) -> str:
    value = json.dumps([user_id, operation, client_key, prompt_version], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]


def request_fingerprint(request: GenerateRequest) -> str:
    canonical = request.model_dump(mode="json")
    value = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]


def stored_trace_id(idempotency_trace: str, model_trace: object) -> str:
    """Persist idempotency identity and the provider trace without a migration."""
    if isinstance(model_trace, str) and model_trace.startswith("tr_"):
        return f"{idempotency_trace}|{model_trace}"
    return idempotency_trace


def idempotency_trace_id(value: str) -> str:
    return value.partition("|")[0]


def model_trace_id(value: str) -> str | None:
    _identity, separator, trace_id = value.partition("|")
    return trace_id if separator and trace_id.startswith("tr_") else None


@router.post("/card-sets", status_code=201)
async def generate_card_set(
    request: GenerateRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(session_scope),
    x_user_id: Annotated[str | None, Header(alias="X-User-ID")] = None,
):
    if not x_user_id:
        raise HTTPException(status_code=401, detail={"code": "USER_ID_REQUIRED"})
    failure = validate_untrusted_input({"pages": request.pages, "estimated_tokens": sum(len(page.text) for page in request.pages) // 4})
    if failure:
        raise HTTPException(status_code=failure.status, detail={"code": failure.code})
    prompt_version = await model_generation_version()
    client_key = idempotency_key or f"demo-{request.document_id}"
    scope = idempotency_identity(x_user_id, "card-sets", client_key, prompt_version)
    fingerprint = request_fingerprint(request)
    trace_prefix = f"idem:{scope}:"
    existing = db.scalar(select(CardSet).where(CardSet.trace_id.like(f"{trace_prefix}%")))
    if existing:
        if idempotency_trace_id(existing.trace_id) != f"{trace_prefix}{fingerprint}":
            raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_CONFLICT"})
        return serialize_set(existing)

    estimated_tokens = max(1, sum(len(page.text) for page in request.pages) // 4)
    decision = budget_limiter.consume(x_user_id or "", estimated_tokens)
    record_budget(decision)
    if not decision.allowed:
        status = 401 if decision.reason == "USER_ID_REQUIRED" else 429
        raise HTTPException(status_code=status, detail={"code": decision.reason})

    model_payload = request.model_dump()
    model_payload.update(
        model_tier=decision.model_tier,
        user_id=x_user_id,
        resource_owner_id=x_user_id,
    )
    result = await call_model("/v1/model/card-sets", model_payload)
    page_text = {page.page: page.text for page in request.pages}
    if not 1 <= len(result.get("cards", [])) <= request.requested_card_count:
        raise HTTPException(status_code=502, detail={"code": "MODEL_OUTPUT_INVALID"})
    for item in result["cards"]:
        failure = validate_model_card(item, page_text)
        if failure:
            raise HTTPException(status_code=failure.status, detail={"code": failure.code})
    document = db.get(Document, request.document_id)
    if not document:
        document = Document(id=request.document_id, pages=[page.model_dump() for page in request.pages])
        db.add(document)
        # The ORM does not expose a CardSet.document relationship, so make the
        # foreign-key ordering explicit for PostgreSQL (SQLite tests do not
        # enforce this constraint by default).
        db.flush()
    card_set = CardSet(
        document_id=request.document_id,
        title=result["title"],
        model=result["model"],
        prompt_version=result["prompt_version"],
        fallback_used=result.get("fallback_used", False),
        trace_id=stored_trace_id(f"{trace_prefix}{fingerprint}", result.get("trace_id")),
        latency_ms=result.get("latency_ms", 0),
        input_tokens=result.get("usage", {}).get("input_tokens", 0),
        output_tokens=result.get("usage", {}).get("output_tokens", 0),
    )
    db.add(card_set)
    db.flush()
    card_fields = {"question", "reference_answer", "source_page", "source_quote", "difficulty"}
    for position, item in enumerate(result["cards"], start=1):
        values = {key: value for key, value in item.items() if key in card_fields}
        db.add(Card(id=item.get("card_id", f"card_{uuid4().hex}"), card_set_id=card_set.id, position=position, **values))
    db.commit()
    db.refresh(card_set)
    response = serialize_set(card_set)
    # Safe provider diagnostic for a newly generated set. It contains only a
    # category such as gemini_http_403, never an API key or provider body.
    response["fallback_reason"] = result.get("fallback_reason")
    response["validation_error"] = result.get("validation_error")
    response["provider_usage"] = result.get("provider_usage")
    return response


@router.post("/card-sets/from-pdf", status_code=201)
async def generate_card_set_from_pdf(
    file: UploadFile = File(...),
    requested_card_count: int = Form(default=5, ge=5, le=10),
    language: str = Form(default="ru", pattern=r"^(ru|en)$"),
    db: Session = Depends(session_scope),
    x_user_id: Annotated[str | None, Header(alias="X-User-ID")] = None,
):
    """Extract text (with OCR for scans) and run the persisted generation flow."""
    failure = validate_untrusted_input({"mime_type": file.content_type})
    if failure:
        raise HTTPException(status_code=failure.status, detail={"code": failure.code})
    raw = await file.read(10 * 1024 * 1024 + 1)
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail={"code": "FILE_TOO_LARGE", "max_bytes": 10 * 1024 * 1024})
    try:
        extracted = extract_pdf_pages(raw)
        pages = [Page(page=page.page, text=page.text) for page in extracted]
    except PdfExtractionError as exc:
        status = 413 if exc.code in {"PDF_TOO_MANY_PAGES"} else 422
        raise HTTPException(status_code=status, detail={"code": exc.code, "message": str(exc)}) from exc
    digest_input = raw
    if any(page.method == "math_layout" for page in extracted):
        # Re-upload after the extractor upgrade must not collide with a set
        # cached from the old flattened math text (or return stale formulas).
        structured = "\n".join(page.text for page in extracted).encode("utf-8")
        digest_input += b"\x00math-layout-v1\x00" + structured
    digest = hashlib.sha256(digest_input).hexdigest()[:24]
    request = GenerateRequest(
        document_id=f"pdf_{digest}",
        language=language,
        pages=pages,
        requested_card_count=requested_card_count,
    )
    # Prompt version is added centrally by generate_card_set after reading AI metadata.
    return await generate_card_set(
        request=request,
        idempotency_key=f"pdf-{digest}-{requested_card_count}-{language}",
        db=db,
        x_user_id=x_user_id,
    )


@router.post("/answer-reviews")
async def review_answer(
    request: ReviewRequest,
    db: Session = Depends(session_scope),
    x_user_id: Annotated[str | None, Header(alias="X-User-ID")] = None,
):
    failure = validate_untrusted_input({"student_answer": request.student_answer})
    if failure:
        raise HTTPException(status_code=failure.status, detail={"code": failure.code})
    study_session = ensure_session_access(db.get(StudySession, request.session_id), x_user_id)
    persisted_card = db.get(Card, request.card.card_id)
    if not persisted_card or persisted_card.card_set_id != study_session.card_set_id:
        raise HTTPException(status_code=403, detail={"code": "CARD_SESSION_MISMATCH"})
    # Never trust reference text supplied by a client. The model reviews the
    # answer against the canonical card stored for this session.
    canonical_card = {
        "card_id": persisted_card.id,
        "question": persisted_card.question,
        "reference_answer": persisted_card.reference_answer,
        "source_page": persisted_card.source_page,
        "source_quote": persisted_card.source_quote,
        "difficulty": persisted_card.difficulty,
    }
    estimated_tokens = max(1, (len(request.student_answer) + len(persisted_card.reference_answer)) // 4)
    decision = budget_limiter.consume(x_user_id or "", estimated_tokens)
    record_budget(decision)
    if not decision.allowed:
        status = 401 if decision.reason == "USER_ID_REQUIRED" else 429
        raise HTTPException(status_code=status, detail={"code": decision.reason})
    result = await call_model(
        "/v1/model/answer-reviews",
        {
            "session_id": request.session_id,
            "card": canonical_card,
            "student_answer": request.student_answer,
            "model_tier": decision.model_tier,
            "user_id": x_user_id,
            "resource_owner_id": x_user_id,
        },
    )
    review = AnswerReview(
        card_id=request.card.card_id,
        student_answer=request.student_answer,
        verdict=result["verdict"],
        feedback=result["feedback"],
        missing_points=result.get("missing_points", []),
        model=result["model"],
        trace_id=result["trace_id"],
        latency_ms=result.get("latency_ms", 0),
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    response = dict(result)
    response["review_id"] = review.id
    response["persisted"] = True
    return response


@router.get("/card-sets/latest")
def latest_card_set(db: Session = Depends(session_scope)):
    card_set = db.scalars(select(CardSet).order_by(CardSet.created_at.desc())).first()
    if not card_set:
        raise HTTPException(status_code=404, detail={"code": "CARD_SET_NOT_FOUND"})
    return serialize_set(card_set)


@router.post("/sessions", status_code=201)
def create_or_resume_session(request: SessionRequest, db: Session = Depends(session_scope)):
    card_set = db.get(CardSet, request.card_set_id)
    if not card_set:
        raise HTTPException(status_code=404, detail={"code": "CARD_SET_NOT_FOUND"})
    study_session = db.scalars(
        select(StudySession)
        .where(
            StudySession.user_id == request.user_id,
            StudySession.card_set_id == request.card_set_id,
            StudySession.completed.is_(False),
        )
        .order_by(StudySession.updated_at.desc())
    ).first()
    if not study_session:
        study_session = StudySession(card_set_id=request.card_set_id, user_id=request.user_id)
        db.add(study_session)
        db.commit()
        db.refresh(study_session)
    return serialize_session(study_session, card_set, db)


@router.get("/sessions/resume")
def resume_latest_session(user_id: str, db: Session = Depends(session_scope)):
    study_session = db.scalars(
        select(StudySession)
        .where(StudySession.user_id == user_id, StudySession.completed.is_(False))
        .order_by(StudySession.updated_at.desc())
    ).first()
    if not study_session:
        raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND"})
    return serialize_session(study_session, db.get(CardSet, study_session.card_set_id), db)


@router.get("/sessions/{session_id}")
def get_session(
    session_id: str,
    db: Session = Depends(session_scope),
    x_user_id: Annotated[str | None, Header(alias="X-User-ID")] = None,
):
    study_session = ensure_session_access(db.get(StudySession, session_id), x_user_id)
    return serialize_session(study_session, db.get(CardSet, study_session.card_set_id), db)


@router.patch("/sessions/{session_id}/progress")
def update_session_progress(session_id: str, request: ProgressRequest, db: Session = Depends(session_scope), x_user_id: Annotated[str | None, Header(alias="X-User-ID")] = None):
    study_session = ensure_session_access(db.get(StudySession, session_id), x_user_id)
    card_set = db.get(CardSet, study_session.card_set_id)
    card_count = len(card_set.cards)
    study_session.current_position = min(request.current_position, card_count)
    study_session.completed = study_session.current_position >= card_count
    study_session.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(study_session)
    return serialize_session(study_session, card_set, db)


@router.put("/sessions/{session_id}/ratings/{card_id}")
def rate_card(session_id: str, card_id: str, request: RatingRequest, db: Session = Depends(session_scope), x_user_id: Annotated[str | None, Header(alias="X-User-ID")] = None):
    study_session = ensure_session_access(db.get(StudySession, session_id), x_user_id)
    card = db.get(Card, card_id)
    if not card:
        raise HTTPException(status_code=404, detail={"code": "CARD_NOT_FOUND"})
    if card.card_set_id != study_session.card_set_id:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN"})
    rating = db.scalars(
        select(CardRating).where(CardRating.session_id == session_id, CardRating.card_id == card_id)
    ).first()
    if not rating:
        rating = CardRating(session_id=session_id, card_id=card_id, value=request.value)
        db.add(rating)
    else:
        rating.value = request.value
        rating.updated_at = datetime.now(timezone.utc)
    db.add(CardRatingEvent(session_id=session_id, card_id=card_id, value=request.value))
    study_session.updated_at = datetime.now(timezone.utc)
    db.commit()
    event_count = len(
        db.scalars(
            select(CardRatingEvent).where(
                CardRatingEvent.session_id == session_id,
                CardRatingEvent.card_id == card_id,
            )
        ).all()
    )
    return {"session_id": session_id, "card_id": card_id, "value": rating.value, "event_count": event_count}


@router.post("/sessions/{session_id}/complete")
def complete_session(session_id: str, request: CompleteRequest, db: Session = Depends(session_scope), x_user_id: Annotated[str | None, Header(alias="X-User-ID")] = None):
    study_session = ensure_session_access(db.get(StudySession, session_id), x_user_id)
    counts = {name: 0 for name in ("correct", "partially_correct", "incorrect", "skipped")}
    for answer in request.answers:
        verdict = answer.get("verdict", "skipped")
        if verdict in counts:
            counts[verdict] += 1
    study_session.completed = True
    study_session.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"session_id": session_id, "status": "completed", "counts": counts}


def serialize_set(card_set: CardSet) -> dict:
    return {
        "card_set_id": card_set.id,
        "title": card_set.title,
        "model": card_set.model,
        "prompt_version": card_set.prompt_version,
        "fallback_used": card_set.fallback_used,
        "trace_id": model_trace_id(card_set.trace_id),
        "latency_ms": card_set.latency_ms,
        "usage": {"input_tokens": card_set.input_tokens, "output_tokens": card_set.output_tokens},
        "cards": [
            {
                "card_id": card.id,
                "question": card.question,
                "reference_answer": card.reference_answer,
                "source_page": card.source_page,
                "source_quote": card.source_quote,
                "difficulty": card.difficulty,
            }
            for card in sorted(card_set.cards, key=lambda value: value.position)
        ],
    }


def serialize_session(study_session: StudySession, card_set: CardSet, db: Session) -> dict:
    ratings = db.scalars(select(CardRating).where(CardRating.session_id == study_session.id)).all()
    data = serialize_set(card_set)
    data.update(
        {
            "session_id": study_session.id,
            "user_id": study_session.user_id,
            "current_position": study_session.current_position,
            "completed": study_session.completed,
            "ratings": {rating.card_id: rating.value for rating in ratings},
        }
    )
    return data
