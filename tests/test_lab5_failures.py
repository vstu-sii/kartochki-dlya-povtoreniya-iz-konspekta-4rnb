import unittest
from unittest.mock import patch

import httpx
from fastapi import HTTPException
from sqlalchemy.exc import OperationalError

from backend.main import database_unavailable
from backend.routers.ai import AI_MAX_ATTEMPTS, AI_TIMEOUT_SECONDS, call_model, is_retryable_model_status


class FailurePolicyTests(unittest.TestCase):
    def test_transient_provider_statuses_are_retried(self):
        self.assertTrue(is_retryable_model_status(429))
        self.assertTrue(is_retryable_model_status(503))
        self.assertFalse(is_retryable_model_status(400))
        self.assertFalse(is_retryable_model_status(403))

    def test_retry_policy_is_bounded(self):
        self.assertGreaterEqual(AI_MAX_ATTEMPTS, 1)
        self.assertLessEqual(AI_MAX_ATTEMPTS, 3)
        self.assertGreaterEqual(AI_TIMEOUT_SECONDS, 1)
        self.assertLessEqual(AI_TIMEOUT_SECONDS, 120)


class _UnavailableClient:
    calls = 0

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, *args, **kwargs):
        type(self).calls += 1
        request = httpx.Request("POST", "http://ai-service/v1/model/card-sets")
        raise httpx.ConnectError("simulated provider outage", request=request)


class FailureInjectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_model_outage_is_retried_and_becomes_stable_503(self):
        _UnavailableClient.calls = 0
        with patch("backend.routers.ai.AI_SERVICE_URL", "http://ai-service:8001"), patch(
            "backend.routers.ai.httpx.AsyncClient", _UnavailableClient
        ):
            with self.assertRaises(HTTPException) as raised:
                await call_model("/v1/model/card-sets", {"pages": []})
        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.detail["code"], "AI_PROVIDER_UNAVAILABLE")
        self.assertEqual(_UnavailableClient.calls, AI_MAX_ATTEMPTS)

    async def test_database_outage_becomes_stable_retryable_503(self):
        error = OperationalError("SELECT 1", {}, Exception("simulated database outage"))
        response = await database_unavailable(None, error)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers["retry-after"], "5")
        self.assertIn(b"DATABASE_UNAVAILABLE", response.body)


if __name__ == "__main__": unittest.main()
