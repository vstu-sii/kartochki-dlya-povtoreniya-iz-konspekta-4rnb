"""Exercise budget decisions through HTTP, plus the actual provider selection branch."""
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

os.environ["AI_SERVICE_URL"] = "inprocess"
os.environ["DATABASE_URL"] = "sqlite:///./test_lab3.db"

from fastapi import HTTPException
from backend.database import SessionLocal, init_db
from backend.routers.ai import GenerateRequest, generate_card_set
from backend.limits.service import DailyBudgetLimiter
from ml.models.baseline import BaselineModel, CHEAP_MODEL


class HttpBudgetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_http_selects_cheap_then_rejects_without_model_call(self):
        pages = [{"page": 1, "text": "A cache stores frequently used data."}]
        with patch.dict(os.environ, {"BUDGET_DEGRADE_RATIO": "0.80"}):
            limiter = DailyBudgetLimiter(request_limit=5, token_limit=10000)
        result = BaselineModel().generate({"pages": pages, "requested_card_count": 5})
        db = SessionLocal()
        with patch("backend.routers.ai.budget_limiter", limiter), patch("backend.routers.ai.call_model", return_value=result) as model:
            tiers = []
            for index in range(6):
                for card in result["cards"]:
                    card["card_id"] = "card_" + uuid4().hex
                request = GenerateRequest(document_id="doc_" + uuid4().hex, pages=pages)
                try:
                    run_immediate(generate_card_set(request, None, db, "quota-user"))
                    status, code = 201, None
                except HTTPException as exc:
                    status = exc.status_code
                    code = exc.detail.get("code")
                self.assertEqual(201 if index < 5 else 429, status)
                if status == 201:
                    tiers.append(model.call_args.args[1]["model_tier"])
            self.assertEqual(["primary"] * 3 + ["cheap"] * 2, tiers)
            self.assertEqual(5, model.call_count)
            self.assertEqual("REQUEST_LIMIT_EXCEEDED", code)
        db.close()

    def test_cheap_tier_selects_cheap_provider_model(self):
        with patch.dict(os.environ, {"MODEL_PROVIDER": "gemini", "GEMINI_API_KEY": "test-placeholder"}):
            model = BaselineModel()
            with patch.object(model, "_call_gemini", return_value={
                "verdict": "correct", "score": 2, "feedback": "Correct", "missing_points": []
            }) as provider:
                model.review({"model_tier": "cheap", "card": {"question": "What is a cache?", "reference_answer": "Fast storage."},
                              "student_answer": "Fast storage."})
            self.assertEqual(CHEAP_MODEL, provider.call_args.args[2])


def run_immediate(coroutine):
    try:
        coroutine.send(None)
    except StopIteration as done:
        return done.value
    finally:
        coroutine.close()
    raise RuntimeError("In-process router coroutine unexpectedly suspended")
