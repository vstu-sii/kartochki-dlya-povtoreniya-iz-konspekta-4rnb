"""Dependency-free Prometheus endpoint and structured production events."""

import json
import logging
import time
from collections import defaultdict
from threading import Lock

from starlette.responses import Response


logger = logging.getLogger("production.events")
_lock = Lock()
_requests: dict[tuple[str, str, str], int] = defaultdict(int)
_latency_sum: dict[tuple[str, str], float] = defaultdict(float)
_latency_count: dict[tuple[str, str], int] = defaultdict(int)
_budgets: dict[tuple[str, str], int] = defaultdict(int)


async def metrics_middleware(request, call_next):
    started = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        route = request.scope.get("route")
        path = route.path if route else request.url.path
        elapsed = time.perf_counter() - started
        with _lock:
            _requests[(request.method, path, str(status))] += 1
            _latency_sum[(request.method, path)] += elapsed
            _latency_count[(request.method, path)] += 1


def metrics_response() -> Response:
    lines = [
        "# HELP flashcards_http_requests_total HTTP requests",
        "# TYPE flashcards_http_requests_total counter",
    ]
    with _lock:
        for (method, path, status), value in sorted(_requests.items()):
            lines.append(f'flashcards_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {value}')
        lines.extend(["# HELP flashcards_http_request_seconds_sum HTTP latency", "# TYPE flashcards_http_request_seconds_sum counter"])
        for (method, path), value in sorted(_latency_sum.items()):
            labels = f'method="{method}",path="{path}"'
            lines.append(f"flashcards_http_request_seconds_sum{{{labels}}} {value:.6f}")
            lines.append(f"flashcards_http_request_seconds_count{{{labels}}} {_latency_count[(method, path)]}")
        lines.extend(["# HELP flashcards_budget_events_total Budget decisions", "# TYPE flashcards_budget_events_total counter"])
        for (decision, tier), value in sorted(_budgets.items()):
            lines.append(f'flashcards_budget_events_total{{decision="{decision}",tier="{tier}"}} {value}')
    return Response("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


def record_budget(decision) -> None:
    label = "allow" if decision.allowed else "reject"
    with _lock:
        _budgets[(label, decision.model_tier)] += 1
    logger.info(json.dumps({"event": "budget_decision", "decision": label, "tier": decision.model_tier}))
