import asyncio
import os
import unittest


os.environ["AI_SERVICE_URL"] = "inprocess"
os.environ["DATABASE_URL"] = "sqlite:///./test_lab3.db"

from backend.database import SessionLocal, init_db  # noqa: E402
from backend.routers.ai import GenerateRequest, ReviewRequest, generate_card_set, review_answer  # noqa: E402


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
            review = ReviewRequest(
                session_id="session_integration",
                card=card_set["cards"][0],
                student_answer=card_set["cards"][0]["reference_answer"],
            )
            result = asyncio.run(review_answer(review, db))
            self.assertEqual("correct", result["verdict"])
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
