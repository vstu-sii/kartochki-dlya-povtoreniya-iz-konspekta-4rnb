"""Exercise budget decisions through HTTP, plus the actual provider selection branch."""
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

os.environ["AI_SERVICE_URL"] = "inprocess"
os.environ["DATABASE_URL"] = "sqlite:///./test_lab3.db"

from fastapi.testclient import TestClient
from backend.main import app
from backend.limits.service import DailyBudgetLimiter
from ml.models.baseline import BaselineModel, CHEAP_MODEL


class HttpBudgetTest(unittest.TestCase):
    def test_http_selects_cheap_then_rejects_without_model_call(self):
        pages = [{"page": 1, "text": "A cache stores frequently used data."}]
        with patch.dict(os.environ, {"BUDGET_DEGRADE_RATIO": "0.80"}):
            limiter = DailyBudgetLimiter(request_limit=5, token_limit=10000)
        result = BaselineModel().generate({"pages": pages, "requested_card_count": 5})
        with TestClient(app) as client, patch("backend.routers.ai.budget_limiter", limiter), patch("backend.routers.ai.call_model", return_value=result) as model:
            tiers = []
            for index in range(6):
                for card in result["cards"]:
                    card["card_id"] = "card_" + uuid4().hex
                response = client.post("/v1/ai/card-sets", headers={"X-User-ID": "quota-user"},
                                       json={"document_id": "doc_" + uuid4().hex, "pages": pages})
                self.assertEqual(201 if index < 5 else 429, response.status_code)
                if index < 5:
                    tiers.append(model.call_args.args[1]["model_tier"])
            self.assertEqual(["primary"] * 3 + ["cheap"] * 2, tiers)
            self.assertEqual(5, model.call_count)
            self.assertEqual("REQUEST_LIMIT_EXCEEDED", response.json()["detail"]["code"])

    def test_cheap_tier_selects_cheap_provider_model(self):
        with patch.dict(os.environ, {"MODEL_PROVIDER": "gemini", "GEMINI_API_KEY": "test-placeholder"}):
            model = BaselineModel()
            with patch.object(model, "_call_gemini", return_value={
                "verdict": "correct", "score": 2, "feedback": "Correct", "missing_points": []
            }) as provider:
                model.review({"model_tier": "cheap", "card": {"question": "What is a cache?", "reference_answer": "Fast storage."},
                              "student_answer": "Fast storage."})
            self.assertEqual(CHEAP_MODEL, provider.call_args.args[2])
