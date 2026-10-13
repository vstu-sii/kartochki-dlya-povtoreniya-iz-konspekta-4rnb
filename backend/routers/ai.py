"""Public AI endpoints: validate, call the model service, then persist results."""

import hashlib
import os
from io import BytesIO
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from pypdf import PdfReader
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import session_scope
from backend.models import AnswerReview, Card, CardSet, Document


router = APIRouter(prefix="/v1/ai", tags=["AI"])
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai-service:8001")


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


async def call_model(path: str, payload: dict) -> dict:
    if AI_SERVICE_URL == "inprocess":
        from ml.models.baseline import BaselineModel

        model = BaselineModel()
        return model.generate(payload) if path.endswith("card-sets") else model.review(payload)

    try:
        async with httpx.AsyncClient(timeout=65.0) as client:
            response = await client.post(f"{AI_SERVICE_URL}{path}", json=payload)
            response.raise_for_status()
            return response.json()
    except (httpx.TimeoutException, httpx.NetworkError) as exc:
        raise HTTPException(status_code=503, detail={"code": "AI_PROVIDER_UNAVAILABLE", "message": str(exc)}) from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.json() if exc.response.headers.get("content-type", "").startswith("application/json") else exc.response.text
        raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc


@router.post("/card-sets", status_code=201)
async def generate_card_set(
    request: GenerateRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(session_scope),
):
    key = idempotency_key or f"demo-{request.document_id}"
    existing = db.scalar(select(CardSet).where(CardSet.trace_id == f"idem:{key}"))
    if existing:
        return serialize_set(existing)

    result = await call_model("/v1/model/card-sets", request.model_dump())
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
        trace_id=f"idem:{key}",
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
    return serialize_set(card_set)


@router.post("/card-sets/from-pdf", status_code=201)
async def generate_card_set_from_pdf(
    file: UploadFile = File(...),
    requested_card_count: int = Form(default=5, ge=5, le=10),
    language: str = Form(default="ru", pattern=r"^(ru|en)$"),
    db: Session = Depends(session_scope),
):
    """Extract the text layer from one PDF and run the normal persisted flow."""
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail={"code": "PDF_REQUIRED"})
    raw = await file.read(10 * 1024 * 1024 + 1)
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail={"code": "PDF_TOO_LARGE", "max_bytes": 10 * 1024 * 1024})
    try:
        reader = PdfReader(BytesIO(raw))
        pages = [
            Page(page=number, text=text)
            for number, page in enumerate(reader.pages, start=1)
            if len(text := (page.extract_text() or "").strip()) >= 10
        ]
    except Exception as exc:
        raise HTTPException(status_code=422, detail={"code": "PDF_PARSE_FAILED"}) from exc
    if not pages:
        raise HTTPException(status_code=422, detail={"code": "PDF_HAS_NO_TEXT_LAYER"})
    digest = hashlib.sha256(raw).hexdigest()[:24]
    request = GenerateRequest(
        document_id=f"pdf_{digest}",
        language=language,
        pages=pages[:40],
        requested_card_count=requested_card_count,
    )
    return await generate_card_set(request, f"pdf-{digest}-{requested_card_count}-{language}", db)


@router.post("/answer-reviews")
async def review_answer(request: ReviewRequest, db: Session = Depends(session_scope)):
    result = await call_model("/v1/model/answer-reviews", request.model_dump())
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
    return result


@router.get("/card-sets/latest")
def latest_card_set(db: Session = Depends(session_scope)):
    card_set = db.scalars(select(CardSet).order_by(CardSet.created_at.desc())).first()
    if not card_set:
        raise HTTPException(status_code=404, detail={"code": "CARD_SET_NOT_FOUND"})
    return serialize_set(card_set)


def serialize_set(card_set: CardSet) -> dict:
    return {
        "card_set_id": card_set.id,
        "title": card_set.title,
        "model": card_set.model,
        "prompt_version": card_set.prompt_version,
        "fallback_used": card_set.fallback_used,
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
