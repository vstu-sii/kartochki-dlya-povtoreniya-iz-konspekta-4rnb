"""Thread-safe daily request/token limits with an explicit cheap-model tier."""

import json
import logging
import os
from dataclasses import dataclass
from datetime import date
from threading import Lock


logger = logging.getLogger("production.budget")


@dataclass(frozen=True)
class BudgetDecision:
    allowed: bool
    model_tier: str
    requests_used: int
    tokens_used: int
    reason: str | None = None
    alert: bool = False


class DailyBudgetLimiter:
    """Small in-process limiter used by the prototype and exercised in CI.

    Production replicas should point this interface at Redis. The important
    security property already holds here: the application, not the model,
    makes the allow/deny/degrade decision.
    """

    def __init__(self, request_limit: int | None = None, token_limit: int | None = None):
        self.request_limit = request_limit or int(os.getenv("MAX_REQUESTS_PER_USER_DAY", "50"))
        self.token_limit = token_limit or int(os.getenv("MAX_TOKENS_PER_USER_DAY", "120000"))
        self.degrade_ratio = float(os.getenv("BUDGET_DEGRADE_RATIO", "0.80"))
        self._lock = Lock()
        self._day = date.today()
        self._usage: dict[str, dict[str, int]] = {}

    def consume(self, user_id: str, estimated_tokens: int) -> BudgetDecision:
        if not user_id or len(user_id) > 128:
            return BudgetDecision(False, "none", 0, 0, "USER_ID_REQUIRED")
        tokens = max(1, estimated_tokens)
        with self._lock:
            self._reset_if_needed()
            usage = self._usage.setdefault(user_id, {"requests": 0, "tokens": 0})
            next_requests = usage["requests"] + 1
            next_tokens = usage["tokens"] + tokens
            if next_requests > self.request_limit:
                return self._deny(user_id, usage, "REQUEST_LIMIT_EXCEEDED")
            if next_tokens > self.token_limit:
                return self._deny(user_id, usage, "TOKEN_LIMIT_EXCEEDED")
            usage.update(requests=next_requests, tokens=next_tokens)
            ratio = max(next_requests / self.request_limit, next_tokens / self.token_limit)
            tier = "cheap" if ratio >= self.degrade_ratio else "primary"
            alert = ratio >= self.degrade_ratio
            if alert:
                self._log_event(user_id, usage, "budget_anomaly", tier)
            return BudgetDecision(True, tier, next_requests, next_tokens, alert=alert)

    def snapshot(self, user_id: str) -> dict[str, int]:
        with self._lock:
            self._reset_if_needed()
            return dict(self._usage.get(user_id, {"requests": 0, "tokens": 0}))

    def reset_for_tests(self) -> None:
        with self._lock:
            self._day = date.today()
            self._usage.clear()

    def _reset_if_needed(self) -> None:
        today = date.today()
        if today != self._day:
            self._day = today
            self._usage.clear()

    def _deny(self, user_id: str, usage: dict[str, int], reason: str) -> BudgetDecision:
        self._log_event(user_id, usage, "budget_rejected", "none", reason)
        return BudgetDecision(False, "none", usage["requests"], usage["tokens"], reason, True)

    @staticmethod
    def _log_event(user_id: str, usage: dict[str, int], event: str, tier: str, reason: str | None = None) -> None:
        logger.warning(
            json.dumps(
                {
                    "event": event,
                    "user_hash": __import__("hashlib").sha256(user_id.encode()).hexdigest()[:12],
                    "requests": usage["requests"],
                    "tokens": usage["tokens"],
                    "model_tier": tier,
                    "reason": reason,
                },
                ensure_ascii=False,
            )
        )


budget_limiter = DailyBudgetLimiter()
