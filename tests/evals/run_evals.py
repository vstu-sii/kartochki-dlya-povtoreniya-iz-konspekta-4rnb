"""Model and input-guard component of the Lab4 full suite; fixed Lab2 mini.

Usage:
  python tests/evals/run_evals.py
  python tests/evals/run_evals.py --mini --min-schema 1 --min-grounding .95 --min-review .85
"""

import argparse
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ml.models.baseline import (  # noqa: E402
    BaselineModel,
    DETERMINISTIC_GENERATION_MODEL,
    PROMPT_VERSION,
    REVIEW_PROMPT_VERSION,
)
from backend.quality_guards import validate_untrusted_input
from ml.tracing.client import TraceClient  # noqa: E402
from dataset_catalog import DATASET_VERSION, dataset_hash, load_dataset


DEFAULT_OUTPUT = ROOT / "artifacts/evals/baseline-results.json"
MINI_IDS = {"GEN-001", "GEN-002", "GEN-003", "GEN-004", "REV-004", "REV-005", "SAFE-001", "SAFE-002"}


def load_cases(mini: bool) -> list[dict]:
    records = load_dataset()
    if not MINI_IDS.issubset({item["id"] for item in records}):
        raise ValueError("Missing fixed mini case")
    return [item for item in records if item["id"] in MINI_IDS] if mini else records


def percentile(values: list[int], percent: float) -> float:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * percent))]


def validate_generated_cards(response: dict, case: dict) -> tuple[bool, bool]:
    cards = response.get("cards")
    requested = case["input"].get("requested_card_count", 5)
    if not isinstance(cards, list) or not 1 <= len(cards) <= requested:
        return False, False
    page_text = {page["page"]: page["text"] for page in case["context"]}
    required_quote = case.get("expected_output", {}).get("required_quote")
    schema_ok = True
    grounding_ok = True
    for card in cards:
        schema_ok &= (
            isinstance(card, dict)
            and isinstance(card.get("card_id"), str)
            and 1 <= len(card.get("question", "")) <= 500
            and 1 <= len(card.get("reference_answer", "")) <= 1200
            and isinstance(card.get("source_page"), int)
            and isinstance(card.get("source_quote"), str)
            and 1 <= len(card.get("source_quote", "")) <= 500
            and card.get("difficulty") in {"basic", "intermediate", "advanced"}
        )
        grounding_ok &= card.get("source_quote", "") in page_text.get(card.get("source_page"), "")
    if required_quote:
        grounding_ok &= any(required_quote in card.get("source_quote", "") for card in cards)
    return bool(schema_ok), bool(grounding_ok)


def run(mini: bool, output: Path) -> dict:
    cases = load_cases(mini)
    trace_path = ROOT / "artifacts/evals/eval-traces.jsonl"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    if trace_path.exists():
        trace_path.unlink()
    model = BaselineModel(TraceClient(str(trace_path)))
    rows, latencies, input_tokens, output_tokens = [], [], 0, 0

    for case in cases:
        started = time.perf_counter()
        operation = case["operation"]
        schema_ok = grounding_ok = verdict_ok = safety_ok = None
        executed, skip_reason = True, None
        if operation == "generate_card":
            response = model.generate(
                {
                    "document_id": f"eval_{case['id'].lower()}",
                    "language": case["input"].get("language", "ru"),
                    "pages": case["context"],
                    "requested_card_count": case["input"].get("requested_card_count", 5),
                    "user_id": "eval-owner",
                    "resource_owner_id": "eval-owner",
                }
            )
            schema_ok, grounding_ok = validate_generated_cards(response, case)
        elif operation == "review_answer":
            source = case["context"][0]
            response = model.review(
                {
                    "session_id": "eval_session",
                    "card": {
                        "card_id": case["id"].lower(),
                        "question": case["input"]["question"],
                        "reference_answer": case["input"]["reference_answer"],
                        "source_page": source["page"],
                        "source_quote": source["text"][:500],
                        "difficulty": "basic",
                    },
                    "student_answer": case["input"]["student_answer"],
                }
            )
            schema_ok = (
                response.get("verdict") in {"correct", "partially_correct", "incorrect"}
                and isinstance(response.get("score"), int)
                and response["score"] in {0, 1, 2}
                and isinstance(response.get("feedback"), str)
                and bool(response["feedback"].strip())
                and isinstance(response.get("missing_points"), list)
                and isinstance(response.get("trace_id"), str)
            )
            verdict_ok = response["verdict"] == case["expected_output"]["verdict"]
        elif operation == "reject_input":
            failure = validate_untrusted_input(case["input"])
            expected = case["expected_output"]
            expected_status = expected.get("http_status", expected.get("status"))
            safety_ok = failure is not None and failure.code == expected.get("code", expected.get("error_code")) and (expected_status is None or failure.status == expected_status)
            response = {}
        else:
            # These cases belong to API/DB E2E, not to BaselineModel. Do not
            # fabricate a pass: report them as skipped until that suite calls
            # the running Compose system.
            executed = False
            skip_reason = "requires_api_or_database_e2e"
            response = {}

        latency = round((time.perf_counter() - started) * 1000)
        if executed:
            latencies.append(latency)
        usage = response.get("usage", {})
        input_tokens += usage.get("input_tokens", 0)
        output_tokens += usage.get("output_tokens", 0)
        rows.append(
            {
                "id": case["id"],
                "operation": operation,
                "executed": executed,
                "skip_reason": skip_reason,
                "actual_verdict": response.get("verdict"),
                "expected_verdict": case.get("expected_output", {}).get("verdict"),
                "schema_ok": schema_ok,
                "grounding_ok": grounding_ok,
                "verdict_ok": verdict_ok,
                "safety_ok": safety_ok,
                "latency_ms": latency,
            }
        )

    def rate(field: str) -> float | None:
        values = [row[field] for row in rows if row[field] is not None]
        return round(sum(values) / len(values), 4) if values else None

    measurable = [value for field in ("schema_ok", "grounding_ok", "verdict_ok") if (value := rate(field)) is not None]
    executed_count = sum(row["executed"] for row in rows)
    report = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "mode": "mini" if mini else "model-and-input-guards",
        "model": DETERMINISTIC_GENERATION_MODEL,
        "prompt_version": f"{PROMPT_VERSION}/{REVIEW_PROMPT_VERSION}",
        "dataset_version": DATASET_VERSION,
        "dataset_sha256": dataset_hash(),
        "dataset_case_count": len(cases),
        "executed_case_count": executed_count,
        "skipped_case_count": len(cases) - executed_count,
        "execution_coverage_rate": round(executed_count / len(cases), 4) if cases else 0,
        "model_case_count": sum(row["operation"] in {"generate_card", "review_answer"} for row in rows),
        "safety_case_count": sum(row["safety_ok"] is not None for row in rows),
        "latency_scope": "local case processing including validation; not API/provider latency",
        "metrics": {
            "schema_pass_rate": rate("schema_ok"),
            "grounded_card_rate": rate("grounding_ok"),
            "review_agreement_rate": rate("verdict_ok"),
            "safety_guard_rate": rate("safety_ok"),
            "model_quality_score": round(statistics.mean(measurable), 4),
            "latency_p50_ms": percentile(latencies, 0.5),
            "latency_p95_ms": percentile(latencies, 0.95),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
        "cases": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["metrics"], ensure_ascii=False))
    return report


def failed_thresholds(report, thresholds):
    return [name for name, minimum in thresholds.items()
            if minimum is not None and (report["metrics"].get(name) is None or report["metrics"][name] < minimum)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mini", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--min-schema", type=float)
    parser.add_argument("--min-grounding", type=float)
    parser.add_argument("--min-review", type=float)
    parser.add_argument("--min-safety", type=float)
    args = parser.parse_args()
    report = run(args.mini, args.output)
    thresholds = {
        "schema_pass_rate": args.min_schema,
        "grounded_card_rate": args.min_grounding,
        "review_agreement_rate": args.min_review,
        "safety_guard_rate": args.min_safety,
    }
    failed = failed_thresholds(report, thresholds)
    if failed:
        print("Thresholds failed: " + ", ".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
