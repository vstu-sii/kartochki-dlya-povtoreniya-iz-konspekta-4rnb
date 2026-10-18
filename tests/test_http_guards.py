"""Exercise router validation and ownership without an external model API."""
import os
import unittest
from io import BytesIO
from unittest.mock import patch
from uuid import uuid4

os.environ["AI_SERVICE_URL"] = "inprocess"
os.environ["DATABASE_URL"] = "sqlite:///./test_lab3.db"

from fastapi import HTTPException
from pypdf import PdfWriter

from backend.database import SessionLocal, init_db
from backend.routers.ai import (
    CardPayload, CompleteRequest, GenerateRequest, ProgressRequest, RatingRequest,
    ReviewRequest, SessionRequest, complete_session, create_or_resume_session,
    generate_card_set, generate_card_set_from_pdf, get_session, rate_card,
    review_answer, update_session_progress,
)


def run_immediate(coroutine):
    try:
        coroutine.send(None)
    except StopIteration as done:
        return done.value
    finally:
        coroutine.close()
    raise RuntimeError("In-process router coroutine unexpectedly suspended")


class MemoryUpload:
    content_type = "application/pdf"

    def __init__(self, payload: bytes):
        self.payload = payload

    async def read(self, _limit: int) -> bytes:
        return self.payload


class HttpGuardsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_limits_and_blank_answer_do_not_call_model(self):
        db = SessionLocal()
        with patch("backend.routers.ai.call_model") as model:
            blank = ReviewRequest(
                session_id="session_test", student_answer="   ",
                card=CardPayload(card_id="card_test", question="Question", reference_answer="Answer",
                                 source_page=1, source_quote="Quote"),
            )
            with self.assertRaises(HTTPException) as caught:
                run_immediate(review_answer(blank, db, None))
            self.assertEqual(422, caught.exception.status_code)
            self.assertEqual("INVALID_REQUEST", caught.exception.detail["code"])

            oversized = GenerateRequest(
                document_id="doc_" + uuid4().hex,
                pages=[{"page": i, "text": "a" * 130000} for i in (1, 2)],
            )
            with self.assertRaises(HTTPException) as caught:
                run_immediate(generate_card_set(oversized, None, db, "http-owner"))
            self.assertEqual(413, caught.exception.status_code)

            pdf = PdfWriter()
            for _ in range(41):
                pdf.add_blank_page(width=100, height=100)
            data = BytesIO()
            pdf.write(data)
            with self.assertRaises(HTTPException) as caught:
                run_immediate(generate_card_set_from_pdf(MemoryUpload(data.getvalue()), 5, "ru", db, "http-owner"))
            self.assertEqual(413, caught.exception.status_code)
            model.assert_not_called()
        db.close()

    def test_owner_header_and_short_document(self):
        db = SessionLocal()
        request = GenerateRequest(
            document_id="doc_" + uuid4().hex,
            pages=[{"page": 1, "text": "Кэш ускоряет доступ к часто используемым данным."}],
        )
        card_set = run_immediate(generate_card_set(request, None, db, "http-owner"))
        cards = card_set["cards"]
        self.assertEqual(1, len(cards))
        session = create_or_resume_session(SessionRequest(card_set_id=card_set["card_set_id"], user_id="http-owner"), db)

        for identity, expected in ((None, 401), ("another-user", 403)):
            with self.assertRaises(HTTPException) as caught:
                get_session(session["session_id"], db, identity)
            self.assertEqual(expected, caught.exception.status_code)
        self.assertEqual(session["session_id"], get_session(session["session_id"], db, "http-owner")["session_id"])

        review = ReviewRequest(session_id=session["session_id"], student_answer=cards[0]["reference_answer"], card=CardPayload(**cards[0]))
        for identity, expected in ((None, 401), ("another-user", 403)):
            with self.assertRaises(HTTPException) as caught:
                run_immediate(review_answer(review, db, identity))
            self.assertEqual(expected, caught.exception.status_code)
        self.assertEqual("correct", run_immediate(review_answer(review, db, "http-owner"))["verdict"])

        protected_calls = (
            lambda: update_session_progress(session["session_id"], ProgressRequest(current_position=0), db, None),
            lambda: rate_card(session["session_id"], cards[0]["card_id"], RatingRequest(value="useful"), db, None),
            lambda: complete_session(session["session_id"], CompleteRequest(answers=[]), db, None),
        )
        for call in protected_calls:
            with self.assertRaises(HTTPException) as caught:
                call()
            self.assertEqual(401, caught.exception.status_code)
        db.close()


if __name__ == "__main__":
    unittest.main()
