import time
import unittest
from datetime import date, timedelta

from backend.limits.service import DailyBudgetLimiter
from ml.cache import TTLCache


class DailyBudgetLimiterTest(unittest.TestCase):
    def test_degrades_at_80_percent_then_rejects(self):
        limiter = DailyBudgetLimiter(request_limit=10, token_limit=100)
        self.assertEqual("primary", limiter.consume("user-1", 60).model_tier)
        degraded = limiter.consume("user-1", 20)
        self.assertTrue(degraded.allowed)
        self.assertEqual("cheap", degraded.model_tier)
        self.assertTrue(degraded.alert)
        rejected = limiter.consume("user-1", 21)
        self.assertFalse(rejected.allowed)
        self.assertEqual("TOKEN_LIMIT_EXCEEDED", rejected.reason)
        self.assertEqual({"requests": 2, "tokens": 80}, limiter.snapshot("user-1"))

    def test_request_limit_missing_identity_and_daily_reset(self):
        limiter = DailyBudgetLimiter(request_limit=2, token_limit=1000)
        self.assertFalse(limiter.consume("", 1).allowed)
        self.assertTrue(limiter.consume("user-2", 1).allowed)
        self.assertTrue(limiter.consume("user-2", 1).allowed)
        self.assertEqual("REQUEST_LIMIT_EXCEEDED", limiter.consume("user-2", 1).reason)
        limiter._day = date.today() - timedelta(days=1)
        reset = limiter.consume("user-2", 1)
        self.assertTrue(reset.allowed)
        self.assertEqual({"requests": 1, "tokens": 1}, limiter.snapshot("user-2"))

    def test_cache_hit_and_ttl_expiry(self):
        cache = TTLCache(ttl_seconds=0.03, max_entries=2)
        cache.put("key", {"value": 1})
        self.assertEqual({"value": 1}, cache.get("key"))
        time.sleep(0.05)
        self.assertIsNone(cache.get("key"))


if __name__ == "__main__":
    unittest.main()
