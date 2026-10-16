"""Historical guard admission versus current HTTP entry points (not LLM exploitation)."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
BASELINE_COMMIT = "0dea82a452586c49404778cb43806d2aba9b5329"


def historical_guard():
    source = subprocess.check_output(
        ["git", "show", f"{BASELINE_COMMIT}:backend/quality_guards.py"], cwd=ROOT
    ).decode("utf-8")
    module = types.ModuleType("lab3_guard_for_security_eval")
    sys.modules[module.__name__] = module
    exec(compile(source, "historical_backend/quality_guards.py", "exec"), module.__dict__)
    return module.validate_untrusted_input, hashlib.sha256(source.encode()).hexdigest()


def current_http_cases(cases):
    os.environ["MODEL_PROVIDER"] = "deterministic"
    os.environ["AI_SERVICE_URL"] = "inprocess"
    db_path = ROOT / "artifacts/security/http-attacks.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.database import Base, engine
    from backend.limits import budget_limiter
    from ml.models.baseline import BaselineModel

    Base.metadata.drop_all(engine)
    budget_limiter.reset_for_tests()
    pages = [{"page": 1, "text": "A cache stores frequently used data."}]
    fixture = BaselineModel().generate({"pages": pages, "requested_card_count": 5})
    rows = []
    with TestClient(app) as client:
        owner = {"X-User-ID": "security-owner"}
        seed = client.post("/v1/ai/card-sets", headers=owner,
                           json={"document_id": "doc_" + uuid4().hex, "pages": pages})
        seed.raise_for_status()
        card_set = seed.json()
        session = client.post("/v1/ai/sessions", json={"card_set_id": card_set["card_set_id"], "user_id": "security-owner"})
        session.raise_for_status()
        for case in cases:
            is_review = case["point"] == "student answer"
            endpoint = "/v1/ai/answer-reviews" if is_review else "/v1/ai/card-sets"
            body = ({"session_id": session.json()["session_id"], "card": card_set["cards"][0], "student_answer": case["text"]}
                    if is_review else {"document_id": "doc_" + uuid4().hex, "pages": [{"page": 1, "text": case["text"]}]})
            response_fixture = ({"verdict": "incorrect", "feedback": "fixture", "missing_points": [],
                                 "model": "test-transport", "trace_id": "trace_" + uuid4().hex}
                                if is_review else fixture)
            for card in fixture["cards"]:
                card["card_id"] = "card_" + uuid4().hex
                if not is_review:
                    card["source_quote"] = case["text"]
            with patch("backend.routers.ai.call_model", return_value=response_fixture) as model:
                response = client.post(endpoint, headers=owner, json=body)
                code = response.json().get("detail", {}).get("code")
                actual = ("block" if response.status_code == 422 and code == "PROMPT_INJECTION_BLOCKED" and model.call_count == 0
                          else "allow" if response.status_code in (200, 201) and model.call_count == 1 else "error")
                rows.append({"id": case["id"], "point": case["point"], "endpoint": endpoint,
                             "expected": case["expected_after"], "actual": actual,
                             "status": response.status_code, "code": code, "model_calls": model.call_count,
                             "passed": actual == case["expected_after"]})

        key = "security-repeat-" + uuid4().hex
        payload = {"document_id": "doc_" + uuid4().hex, "pages": pages}
        created = client.post("/v1/ai/card-sets", headers={**owner, "Idempotency-Key": key}, json=payload)
        created.raise_for_status()
        with patch("backend.routers.ai.call_model") as model:
            anonymous = client.post("/v1/ai/card-sets", headers={"Idempotency-Key": key}, json=payload)
        rows.append({"id": "Q4-AUTH-01", "point": "anonymous idempotency replay",
                     "expected": "deny_without_disclosing_cards", "actual_status": anonymous.status_code,
                     "cards_disclosed": bool(anonymous.json().get("cards")), "model_calls": model.call_count,
                     "passed": anonymous.status_code in (401, 403) and not anonymous.json().get("cards")})
    engine.dispose()
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("before", "after"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).with_name("attacks.jsonl")
    cases = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not cases or len({c["id"] for c in cases}) != len(cases):
        raise ValueError("Empty or duplicate attack set")
    if args.mode == "before":
        guard, digest = historical_guard()
        rows = []
        for case in cases:
            payload = ({"student_answer": case["text"]} if case["point"] == "student answer"
                       else {"pages": [{"page": 1, "text": case["text"]}]})
            failure = guard(payload)
            actual = "allow" if failure is None else "block"
            rows.append({"id": case["id"], "point": case["point"], "expected": case["expected_before"],
                         "actual": actual, "passed": actual == case["expected_before"]})
        metadata = {"baseline_commit": BASELINE_COMMIT, "guard_sha256": digest,
                    "scope": "historical input guard admission, not model exploitation"}
    else:
        rows = current_http_cases(cases)
        metadata = {"scope": "current HTTP API, extracted PDF text/answer; model transport mocked; no binary PDF parsing"}
    result = {"run_at": datetime.now(timezone.utc).isoformat(), "mode": args.mode,
              "attack_set_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "case_count": len(rows), "passed": sum(r["passed"] for r in rows),
              "failed": sum(not r["passed"] for r in rows), **metadata, "cases": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("mode", "case_count", "passed", "failed")}))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
