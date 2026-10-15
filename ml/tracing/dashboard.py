"""Dependency-free dashboard for local LLM traces."""

import html
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


TRACE_FILE = Path(os.getenv("TRACE_FILE", "/data/traces.jsonl"))
PORT = int(os.getenv("PORT", "3000"))


def read_traces() -> list[dict]:
    if not TRACE_FILE.exists():
        return []
    return [json.loads(line) for line in TRACE_FILE.read_text(encoding="utf-8").splitlines() if line.strip()][-100:][::-1]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        traces = read_traces()
        if self.path == "/health":
            self._send("application/json", json.dumps({"status": "ok", "traces": len(traces)}))
            return
        if self.path == "/api/traces":
            self._send("application/json", json.dumps(traces, ensure_ascii=False))
            return
        rows = "".join(
            f"<tr><td>{html.escape(item['timestamp'])}</td><td>{html.escape(item['operation'])}</td>"
            f"<td>{html.escape(item['model'])}</td><td>{item['latency_ms']} ms</td>"
            f"<td><details><summary>prompt / response</summary><pre>{html.escape(item['prompt_preview'])}\n\n{html.escape(json.dumps(item['response'], ensure_ascii=False, indent=2))}</pre></details></td></tr>"
            for item in traces
        ) or "<tr><td colspan='5'>Вызовов пока нет</td></tr>"
        page = f"""<!doctype html><meta charset='utf-8'><title>LLM traces</title>
        <style>body{{font:14px system-ui;margin:2rem;background:#101827;color:#e5e7eb}}table{{width:100%;border-collapse:collapse}}td,th{{padding:.7rem;border:1px solid #374151;vertical-align:top}}pre{{white-space:pre-wrap;max-width:70vw}}</style>
        <h1>LLM traces</h1><p>Промпт и структурированный ответ каждого вызова.</p>
        <table><thead><tr><th>Время</th><th>Операция</th><th>Модель</th><th>Latency</th><th>Данные</th></tr></thead><tbody>{rows}</tbody></table>"""
        self._send("text/html; charset=utf-8", page)

    def _send(self, content_type: str, value: str):
        body = value.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
