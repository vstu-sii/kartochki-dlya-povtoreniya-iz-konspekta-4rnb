"""Small JSONL tracing SDK with prompt/response redaction limits."""

import json
import os
from hashlib import sha256
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock


class TraceClient:
    _lock = Lock()

    def __init__(self, path: str | None = None):
        self.path = Path(path or os.getenv("TRACE_FILE", "artifacts/traces.jsonl"))

    def record(self, trace_id: str, operation: str, model: str, prompt: str, response: dict, latency_ms: int, fallback_used: bool) -> None:
        keep_content = os.getenv("TRACE_CONTENT", "false").lower() == "true"
        response_view = response if keep_content else {
            "verdict": response.get("verdict"),
            "card_count": len(response.get("cards", [])),
            "prompt_version": response.get("prompt_version"),
            "usage": response.get("usage", {}),
            "fallback_reason": response.get("fallback_reason"),
            "cache_hit": response.get("cache_hit", False),
            "tool_status": response.get("tool_status"),
        }
        event = {
            "trace_id": trace_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "model": model,
            "prompt_sha256": sha256(prompt.encode("utf-8")).hexdigest(),
            "prompt_chars": len(prompt),
            "prompt_preview": prompt[:2_000] if keep_content else "[redacted]",
            "response": response_view,
            "latency_ms": latency_ms,
            "fallback_used": fallback_used,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
        # Promtail collects stdout, so LLM traces are available beside service
        # logs without granting Grafana access to prompts or uploaded PDFs.
        print(json.dumps({"event": "llm_trace", **event}, ensure_ascii=False), flush=True)
