"""Persisted entities for generated cards and answer reviews."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(255), default="pasted-text.txt")
    pages: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class CardSet(Base):
    __tablename__ = "card_sets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("set"))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    model: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(32))
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    trace_id: Mapped[str] = mapped_column(String(128), unique=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    cards: Mapped[list["Card"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    card_set_id: Mapped[str] = mapped_column(ForeignKey("card_sets.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    question: Mapped[str] = mapped_column(String(500))
    reference_answer: Mapped[str] = mapped_column(String(1200))
    source_page: Mapped[int] = mapped_column(Integer)
    source_quote: Mapped[str] = mapped_column(String(500))
    difficulty: Mapped[str] = mapped_column(String(24), default="basic")


class AnswerReview(Base):
    __tablename__ = "answer_reviews"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("review"))
    card_id: Mapped[str] = mapped_column(String(64), index=True)
    student_answer: Mapped[str] = mapped_column(Text)
    verdict: Mapped[str] = mapped_column(String(32))
    feedback: Mapped[str] = mapped_column(String(600))
    missing_points: Mapped[list] = mapped_column(JSON, default=list)
    model: Mapped[str] = mapped_column(String(100))
    trace_id: Mapped[str] = mapped_column(String(128), unique=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class StudySession(Base):
    """Persisted progress so a learner can continue after a restart."""

    __tablename__ = "study_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("session"))
    card_set_id: Mapped[str] = mapped_column(ForeignKey("card_sets.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    current_position: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class CardRating(Base):
    """The latest useful/not-useful rating for one card in one session."""

    __tablename__ = "card_ratings"
    __table_args__ = (UniqueConstraint("session_id", "card_id", name="uq_rating_session_card"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("rating"))
    session_id: Mapped[str] = mapped_column(ForeignKey("study_sessions.id", ondelete="CASCADE"), index=True)
    card_id: Mapped[str] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), index=True)
    value: Mapped[str] = mapped_column(String(16))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
