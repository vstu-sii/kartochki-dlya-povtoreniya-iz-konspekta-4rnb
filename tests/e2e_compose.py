"""Black-box smoke test for the running Compose system."""

import json
import urllib.request


BASE = "http://127.0.0.1:8080"


def request(path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json", "Idempotency-Key": "ci-e2e-lab3"},
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        return json.load(response)


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
review = request(
    "/api/v1/ai/answer-reviews",
    {"session_id": "session_ci", "card": card, "student_answer": card["reference_answer"]},
)
assert review["verdict"] in {"correct", "partial", "incorrect"}
print("E2E OK: UI gateway -> Application API -> AI Service -> PostgreSQL -> review")
