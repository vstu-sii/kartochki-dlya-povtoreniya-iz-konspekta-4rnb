"""Black-box smoke test for the running Compose system."""

import json
import urllib.error
import urllib.request


BASE = "http://127.0.0.1:8080"


def request(path: str, payload: dict | None = None, method: str | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Idempotency-Key": "ci-e2e-lab3"},
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{req.get_method()} {path} returned HTTP {exc.code}: {body}") from exc


created = request(
    "/api/v1/ai/card-sets",
    {
        "document_id": "doc_ci_e2e_lab3",
        "language": "ru",
        "pages": [
            {
                "page": 1,
                "text": "Кэш процессора хранит часто используемые данные и уменьшает время доступа к оперативной памяти.",
            }
        ],
        "requested_card_count": 5,
    },
)
assert len(created["cards"]) == 5
latest = request("/api/v1/ai/card-sets/latest")
assert latest["card_set_id"] == created["card_set_id"]
card = created["cards"][0]
session = request(
    "/api/v1/ai/sessions",
    {"card_set_id": created["card_set_id"], "user_id": "ci-e2e-user"},
)
review = request(
    "/api/v1/ai/answer-reviews",
    {"session_id": session["session_id"], "card": card, "student_answer": card["reference_answer"]},
)
assert review["verdict"] in {"correct", "partially_correct", "incorrect"}
request(
    f"/api/v1/ai/sessions/{session['session_id']}/ratings/{card['card_id']}",
    {"value": "useful"},
    "PUT",
)
request(
    f"/api/v1/ai/sessions/{session['session_id']}/progress",
    {"current_position": 1},
    "PATCH",
)
restored = request(f"/api/v1/ai/sessions/{session['session_id']}")
assert restored["current_position"] == 1
assert restored["ratings"][card["card_id"]] == "useful"
print("E2E OK: UI -> API -> model -> DB -> review -> rating -> resumed progress")
