"""Small JSONL tracing SDK with prompt/response redaction limits."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock


class TraceClient:
    _lock = Lock()

    def __init__(self, path: str | None = None):
        self.path = Path(path or os.getenv("TRACE_FILE", "artifacts/traces.jsonl"))

    def record(self, trace_id: str, operation: str, model: str, prompt: str, response: dict, latency_ms: int, fallback_used: bool) -> None:
        event = {
            "trace_id": trace_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "model": model,
            "prompt_preview": prompt[:2_000],
            "response": response,
            "latency_ms": latency_ms,
            "fallback_used": fallback_used,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
