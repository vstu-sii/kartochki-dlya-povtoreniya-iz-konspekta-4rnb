"""Bounded read-only source lookup with ownership and deadline enforcement."""

from __future__ import annotations

import json
import logging
import time
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass
from threading import BoundedSemaphore


logger = logging.getLogger("model.source_lookup")


class ToolTimeout(RuntimeError):
    """Compatibility exception retained for older callers."""


@dataclass(frozen=True)
class SourceLookupRequest:
    user_id: str
    resource_owner_id: str
    query: str
    pages: list[dict]
    max_results: int = 3


@dataclass(frozen=True)
class SourceLookupResult:
    status: str
    passages: list[dict]
    elapsed_ms: float = 0.0
    cache_hit: bool = False
    error_code: str | None = None


def build_retrieval_query(pages: list[dict], limit_per_page: int = 200) -> str:
    """Build exactly the query used by the production generation pipeline."""
    return " ".join(str(page.get("text", ""))[:limit_per_page] for page in pages).strip()


class SourceLookupTool:
    """A bounded adapter around a synchronous lookup implementation.

    Python cannot safely kill a running thread. A timed-out lookup therefore
    finishes in the background, while the request returns at its deadline.
    One process accepts at most eight running/queued operations, so repeated
    timeouts cannot create an unbounded number of worker threads.
    """

    name = "lookup_source"
    _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="source-lookup")
    _slots = BoundedSemaphore(8)

    def __init__(self, timeout_seconds: float = 1.0):
        self.timeout_seconds = max(0.001, float(timeout_seconds))

    def run(self, request: SourceLookupRequest) -> SourceLookupResult:
        started = time.perf_counter()
        if not request.user_id or request.user_id != request.resource_owner_id:
            return self._result("forbidden", started, error_code="TOOL_FORBIDDEN")
        if not self._slots.acquire(blocking=False):
            return self._result("error", started, error_code="TOOL_BUSY")

        future: Future = self._executor.submit(self._lookup, request)
        future.add_done_callback(lambda _future: self._slots.release())
        try:
            passages = future.result(timeout=self.timeout_seconds)
        except FutureTimeout:
            future.cancel()
            return self._result("timeout", started, error_code="TOOL_TIMEOUT")
        except Exception:
            logger.exception("source lookup failed")
            return self._result("error", started, error_code="TOOL_ERROR")

        if not passages:
            return self._result("empty", started)
        return self._result("success", started, passages=passages)

    def _result(
        self,
        status: str,
        started: float,
        *,
        passages: list[dict] | None = None,
        error_code: str | None = None,
    ) -> SourceLookupResult:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        event = {
            "event": "source_lookup",
            "status": status,
            "elapsed_ms": elapsed_ms,
            "cache_hit": False,
        }
        if error_code:
            event["error_code"] = error_code
        logger.info(json.dumps(event, ensure_ascii=False))
        return SourceLookupResult(status, passages or [], elapsed_ms, False, error_code)

    @staticmethod
    def _lookup(request: SourceLookupRequest) -> list[dict]:
        terms = {term.lower() for term in request.query.split() if len(term) > 2}
        ranked = []
        for page in request.pages:
            text = str(page.get("text", ""))
            score = sum(term in text.lower() for term in terms)
            ranked.append((score, page))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [
            {"page": page["page"], "text": str(page["text"])[:4000]}
            for score, page in ranked[: max(1, min(request.max_results, 5))]
            if score > 0 or not terms
        ]
