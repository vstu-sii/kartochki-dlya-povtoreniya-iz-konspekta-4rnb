"""Reset only the dedicated Lab 6 demo records and seed a realistic session."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sqlalchemy import delete, select  # noqa: E402

from backend.database import SessionLocal, init_db  # noqa: E402
from backend.models import (  # noqa: E402
    AnswerReview,
    Card,
    CardRating,
    CardRatingEvent,
    CardSet,
    Document,
    StudySession,
)


FIXTURE = Path(__file__).with_name("demo_data.json")


def reset_demo() -> dict:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    document_id = data["document"]["id"]
    card_set_id = data["card_set"]["id"]
    session_id = data["session"]["id"]
    card_ids = [card["id"] for card in data["cards"]]
    now = datetime.now(timezone.utc)

    init_db()
    with SessionLocal.begin() as db:
        # Delete in dependency order. Only fixed demo IDs are touched; real
        # student sessions and uploaded documents are never selected.
        db.execute(delete(CardRatingEvent).where(CardRatingEvent.session_id == session_id))
        db.execute(delete(CardRating).where(CardRating.session_id == session_id))
        db.execute(delete(AnswerReview).where(AnswerReview.card_id.in_(card_ids)))
        db.execute(delete(StudySession).where(StudySession.id == session_id))
        db.execute(delete(Card).where(Card.card_set_id == card_set_id))
        db.execute(delete(CardSet).where(CardSet.id == card_set_id))
        db.execute(delete(Document).where(Document.id == document_id))

        db.add(Document(**data["document"], created_at=now))
        db.add(CardSet(
            **data["card_set"],
            document_id=document_id,
            created_at=now,
        ))
        db.add_all(Card(**card, card_set_id=card_set_id) for card in data["cards"])
        db.add(StudySession(
            **data["session"],
            card_set_id=card_set_id,
            created_at=now,
            updated_at=now,
        ))
        rating = data["rating"]
        db.add(CardRating(
            id=rating["id"],
            session_id=session_id,
            card_id=rating["card_id"],
            value=rating["value"],
            updated_at=now,
        ))
        db.add(CardRatingEvent(
            id=rating["event_id"],
            session_id=session_id,
            card_id=rating["card_id"],
            value=rating["value"],
            created_at=now,
        ))

    with SessionLocal() as db:
        cards = db.scalars(select(Card).where(Card.card_set_id == card_set_id)).all()
        session = db.get(StudySession, session_id)
        rating_count = len(db.scalars(select(CardRating).where(CardRating.session_id == session_id)).all())
    return {
        "status": "ready",
        "demo_user": data["session"]["user_id"],
        "card_set_id": card_set_id,
        "cards": len(cards),
        "current_position": session.current_position if session else None,
        "ratings": rating_count,
    }


if __name__ == "__main__":
    print(json.dumps(reset_demo(), ensure_ascii=False, indent=2))
