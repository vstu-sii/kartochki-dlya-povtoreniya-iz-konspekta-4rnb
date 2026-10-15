"""Dataset-driven application/DB evals for non-model operations.

Unlike the model runner, this script invokes the real guard, router and ORM
code. It deliberately uses a temporary SQLite database so every case starts
from known state and remains reproducible in CI.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
DB_PATH = ROOT / "artifacts/evals/application-evals.db"
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["AI_SERVICE_URL"] = "inprocess"

from fastapi import HTTPException  # noqa: E402
from sqlalchemy import func, select  # noqa: E402

from backend.database import Base, SessionLocal, engine  # noqa: E402
from backend.models import Card, CardRating, CardRatingEvent, CardSet, Document, StudySession  # noqa: E402
from backend.quality_guards import validate_model_card, validate_untrusted_input  # noqa: E402
from backend.routers.ai import CompleteRequest, RatingRequest, complete_session, get_session, rate_card  # noqa: E402


DATASETS = (
    ROOT / "docs/quality/golden-dataset/dataset.jsonl",
    ROOT / "docs/quality/golden-dataset/dataset-v2-additions.jsonl",
)
OUTPUT = ROOT / "artifacts/evals/application-results.json"
MODEL_OPERATIONS = {"generate_card", "review_answer"}


def load_cases() -> list[dict]:
    cases = []
    for path in DATASETS:
        cases.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return [case for case in cases if case["operation"] not in MODEL_OPERATIONS]


def reset_database() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def error_code(exc: HTTPException) -> str:
    return exc.detail.get("code", "") if isinstance(exc.detail, dict) else str(exc.detail)


def seed_state(db, case: dict) -> tuple[str, str]:
    expected = case["expected_output"]
    requested_session = case["input"].get("session_id", "session_eval")
    requested_card = case["input"].get("card_id", "card_eval")
    session_id = "session_missing" if requested_session == "missing" else requested_session
    card_id = "card_missing" if requested_card == "missing" else requested_card

    db.add(Document(id="doc_eval", pages=[{"page": 1, "text": "Проверяемый учебный фрагмент."}]))
    db.add(Document(id="doc_other", pages=[{"page": 1, "text": "Другой документ."}]))
    db.flush()
    db.add_all(
        [
            CardSet(id="set_eval", document_id="doc_eval", title="Eval", model="baseline", prompt_version="cards-v1.1", trace_id=f"trace-{case['id']}"),
            CardSet(id="set_other", document_id="doc_other", title="Other", model="baseline", prompt_version="cards-v1.1", trace_id=f"trace-other-{case['id']}"),
        ]
    )
    db.flush()

    if expected.get("code") != "CARD_NOT_FOUND":
        owner_set = "set_other" if expected.get("code") == "FORBIDDEN" and case["operation"] == "rate_card" else "set_eval"
        db.add(Card(id=card_id, card_set_id=owner_set, position=1, question="Q", reference_answer="A", source_page=1, source_quote="Проверяемый учебный фрагмент.", difficulty="basic"))

    if expected.get("code") != "SESSION_NOT_FOUND":
        updated_at = datetime.now(timezone.utc)
        if expected.get("code") == "SESSION_EXPIRED":
            updated_at -= timedelta(days=31)
        db.add(StudySession(id=session_id, card_set_id="set_eval", user_id="owner", current_position=case["input"].get("current_position", 0), updated_at=updated_at))
    db.commit()
    return session_id, card_id


def evaluate_guard(case: dict) -> tuple[bool, dict]:
    expected = case["expected_output"]
    failure = validate_untrusted_input(case["input"])
    expected_code = expected.get("code", expected.get("error_code"))
    expected_status = expected.get("http_status")
    ok = failure is not None and failure.code == expected_code and (expected_status is None or failure.status == expected_status)
    return ok, {"actual_code": failure.code if failure else None, "actual_status": failure.status if failure else 200}


def evaluate_model_output(case: dict) -> tuple[bool, dict]:
    failure = validate_model_card(case["input"]["card"], {1: "Разрешённый фрагмент."})
    expected = case["expected_output"]
    ok = failure is not None and failure.code == expected.get("code") and expected.get("accepted") is False
    return ok, {"actual_code": failure.code if failure else None, "accepted": failure is None}


def evaluate_rating(case: dict) -> tuple[bool, dict]:
    reset_database()
    db = SessionLocal()
    try:
        session_id, card_id = seed_state(db, case)
        expected = case["expected_output"]
        values = []
        if "first" in case["input"]:
            values = [case["input"]["first"], case["input"]["second"]]
        else:
            value = "useful" if case["input"].get("useful", True) else "not_useful"
            values = [value, value] if expected.get("idempotent") else [value]
            if expected.get("replaces_previous"):
                values = ["not_useful" if value == "useful" else "useful", value]
        result = None
        for value in values:
            result = rate_card(session_id, card_id, RatingRequest(value=value), db, "owner")
        rating_count = db.scalar(select(func.count()).select_from(CardRating))
        event_count = db.scalar(select(func.count()).select_from(CardRatingEvent))
        current = result["value"] if result else None
        expected_value = expected.get("current_rating")
        if expected_value is None and "useful" in expected:
            expected_value = "useful" if expected["useful"] else "not_useful"
        ok = bool(result) and rating_count == 1
        if expected_value is not None:
            ok &= current == expected_value
        if "event_count" in expected:
            ok &= event_count == expected["event_count"]
        return ok, {"current_rating": current, "rating_rows": rating_count, "event_count": event_count}
    except HTTPException as exc:
        expected_code = case["expected_output"].get("code")
        return error_code(exc) == expected_code, {"actual_code": error_code(exc), "actual_status": exc.status_code}
    finally:
        db.close()


def evaluate_session(case: dict) -> tuple[bool, dict]:
    reset_database()
    db = SessionLocal()
    try:
        session_id, _ = seed_state(db, case)
        expected = case["expected_output"]
        if case["operation"] == "resume_session":
            user = "intruder" if expected.get("code") == "FORBIDDEN" else "owner"
            result = get_session(session_id, db, user)
            ok = result["current_position"] == case["input"].get("current_position", result["current_position"])
            return ok, {"resumed": True, "position": result["current_position"]}
        request = CompleteRequest(answers=case["input"].get("answers", []))
        result = complete_session(session_id, request, db, "owner")
        if expected.get("idempotent"):
            result = complete_session(session_id, request, db, "owner")
        ok = result["status"] == expected.get("status")
        if "counts" in expected:
            ok &= result["counts"] == expected["counts"]
        return ok, result
    except HTTPException as exc:
        expected_code = case["expected_output"].get("code")
        return error_code(exc) == expected_code, {"actual_code": error_code(exc), "actual_status": exc.status_code}
    finally:
        db.close()


def main() -> int:
    rows = []
    for case in load_cases():
        if case["operation"] == "reject_input":
            passed, actual = evaluate_guard(case)
        elif case["operation"] == "validate_model_output":
            passed, actual = evaluate_model_output(case)
        elif case["operation"] == "rate_card":
            passed, actual = evaluate_rating(case)
        else:
            passed, actual = evaluate_session(case)
        rows.append({"id": case["id"], "operation": case["operation"], "passed": bool(passed), **actual})

    passed_count = sum(row["passed"] for row in rows)
    report = {
        "dataset_version": "lab3-v2",
        "suite": "application-api-db",
        "case_count": len(rows),
        "passed_count": passed_count,
        "failed_count": len(rows) - passed_count,
        "pass_rate": round(passed_count / len(rows), 4),
        "cases": rows,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("case_count", "passed_count", "failed_count", "pass_rate")}))
    return 0 if passed_count == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
