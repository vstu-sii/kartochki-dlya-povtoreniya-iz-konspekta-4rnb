import asyncio
import os
import unittest


os.environ["AI_SERVICE_URL"] = "inprocess"
os.environ["DATABASE_URL"] = "sqlite:///./test_lab3.db"

from backend.database import SessionLocal, init_db  # noqa: E402
from backend.routers.ai import (  # noqa: E402
    GenerateRequest,
    ProgressRequest,
    RatingRequest,
    ReviewRequest,
    SessionRequest,
    create_or_resume_session,
    get_session,
    generate_card_set,
    rate_card,
    review_answer,
    update_session_progress,
)


class ApiFlowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_ui_api_model_database_path(self):
        db = SessionLocal()
        try:
            request = GenerateRequest(
                document_id="doc_integration_001",
                pages=[{"page": 1, "text": "Кэш ускоряет доступ к часто используемым данным."}],
                requested_card_count=5,
            )
            card_set = asyncio.run(generate_card_set(request, "integration-key-0001", db))
            self.assertEqual(5, len(card_set["cards"]))
            study_session = create_or_resume_session(
                SessionRequest(card_set_id=card_set["card_set_id"], user_id="integration-user"), db
            )
            self.assertEqual(0, study_session["current_position"])
            review = ReviewRequest(
                session_id=study_session["session_id"],
                card=card_set["cards"][0],
                student_answer=card_set["cards"][0]["reference_answer"],
            )
            result = asyncio.run(review_answer(review, db))
            self.assertEqual("correct", result["verdict"])
            card_id = card_set["cards"][0]["card_id"]
            rate_card(study_session["session_id"], card_id, RatingRequest(value="useful"), db)
            rate_card(study_session["session_id"], card_id, RatingRequest(value="not_useful"), db)
            update_session_progress(study_session["session_id"], ProgressRequest(current_position=1), db)
            restored = get_session(study_session["session_id"], db)
            self.assertEqual(1, restored["current_position"])
            self.assertEqual("not_useful", restored["ratings"][card_id])
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
