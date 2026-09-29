"""AI Service contract stub; real provider integration starts in Lab 3."""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


PORT = int(os.getenv("PORT", "8001"))
PRIMARY_MODEL = os.getenv("LLM_PRIMARY_MODEL", "gemini-3.8-flash")
FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "gemini-3.5-flash-lite")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path != "/health":
            self.send_error(404)
            return
        body = json.dumps(
            {
                "service": "ai-service",
                "status": "ok",
                "implementation": "lab2-stub",
                "primary_model": PRIMARY_MODEL,
                "fallback_model": FALLBACK_MODEL,
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A002
        print(json.dumps({"service": "ai-service", "message": format % args}))


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
