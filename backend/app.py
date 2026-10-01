"""Dependency-free HTTP stub for Lab 2 container contracts."""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


SERVICE_NAME = os.getenv("SERVICE_NAME", "app-api")
PORT = int(os.getenv("PORT", "8000"))


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - stdlib interface
        if self.path not in {"/", "/health"}:
            self.send_error(404)
            return
        payload = {
            "service": SERVICE_NAME,
            "status": "ok",
            "implementation": "lab2-stub",
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A002
        print(json.dumps({"service": SERVICE_NAME, "message": format % args}))


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
