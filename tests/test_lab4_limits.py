import unittest

from backend.limits.service import DailyBudgetLimiter


class DailyBudgetLimiterTest(unittest.TestCase):
    def test_degrades_then_rejects_token_anomaly(self):
        limiter = DailyBudgetLimiter(request_limit=10, token_limit=100)
        self.assertEqual("primary", limiter.consume("user-1", 60).model_tier)
        degraded = limiter.consume("user-1", 20)
        self.assertTrue(degraded.allowed)
        self.assertEqual("cheap", degraded.model_tier)
        rejected = limiter.consume("user-1", 21)
        self.assertFalse(rejected.allowed)
        self.assertEqual("TOKEN_LIMIT_EXCEEDED", rejected.reason)

    def test_request_limit_and_missing_identity(self):
        limiter = DailyBudgetLimiter(request_limit=2, token_limit=1000)
        self.assertFalse(limiter.consume("", 1).allowed)
        self.assertTrue(limiter.consume("user-2", 1).allowed)
        self.assertTrue(limiter.consume("user-2", 1).allowed)
        self.assertEqual("REQUEST_LIMIT_EXCEEDED", limiter.consume("user-2", 1).reason)


if __name__ == "__main__":
    unittest.main()
