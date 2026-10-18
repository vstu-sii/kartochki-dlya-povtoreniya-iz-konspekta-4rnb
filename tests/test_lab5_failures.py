import unittest

from backend.routers.ai import AI_MAX_ATTEMPTS, AI_TIMEOUT_SECONDS, is_retryable_model_status


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


if __name__ == "__main__": unittest.main()
