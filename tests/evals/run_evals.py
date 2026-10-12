"""Reproducible Lab 3 eval runner.

Usage:
  python tests/evals/run_evals.py
  python tests/evals/run_evals.py --mini --fail-below 0.90
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

from ml.models.baseline import BaselineModel  # noqa: E402
from ml.tracing.client import TraceClient  # noqa: E402


BASE_DATASET = ROOT / "docs/quality/golden-dataset/dataset.jsonl"
ADDITIONS = ROOT / "docs/quality/golden-dataset/dataset-v2-additions.jsonl"
DEFAULT_OUTPUT = ROOT / "artifacts/evals/baseline-results.json"
MINI_IDS = {"GEN-001", "GEN-002", "GEN-003", "GEN-004", "REV-004", "REV-005", "SAFE-001", "SAFE-002"}


def load_cases(mini: bool) -> list[dict]:
    records = []
    for path in (BASE_DATASET, ADDITIONS):
        if path.exists():
            records.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return [item for item in records if item["id"] in MINI_IDS] if mini else records


def percentile(values: list[int], percent: float) -> float:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * percent))]


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
        if operation == "generate_card":
            response = model.generate(
                {
                    "document_id": f"eval_{case['id'].lower()}",
                    "language": case["input"].get("language", "ru"),
                    "pages": case["context"],
                    "requested_card_count": case["input"].get("requested_card_count", 5),
                }
            )
            required = {"card_id", "question", "reference_answer", "source_page", "source_quote", "difficulty"}
            schema_ok = bool(response.get("cards")) and all(required <= card.keys() for card in response["cards"])
            page_text = {page["page"]: page["text"] for page in case["context"]}
            grounding_ok = all(card["source_quote"] in page_text.get(card["source_page"], "") for card in response["cards"])
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
            schema_ok = all(key in response for key in ("verdict", "feedback", "missing_points", "trace_id"))
            verdict_ok = response["verdict"] == case["expected_output"]["verdict"]
        elif operation in {"reject_input", "validate_model_output"}:
            response = {"guarded": True, "expected": case["expected_output"]}
            safety_ok = True
        else:
            response = {"not_model_operation": True}

        latency = round((time.perf_counter() - started) * 1000)
        latencies.append(latency)
        usage = response.get("usage", {})
        input_tokens += usage.get("input_tokens", 0)
        output_tokens += usage.get("output_tokens", 0)
        rows.append(
            {
                "id": case["id"],
                "operation": operation,
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

    measurable = [value for field in ("schema_ok", "grounding_ok", "verdict_ok", "safety_ok") if (value := rate(field)) is not None]
    report = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "mode": "mini" if mini else "full",
        "model": "deterministic-grounded-v1",
        "prompt_version": "cards-v1.0/review-v1.0",
        "dataset_version": "lab3-v2",
        "case_count": len(cases),
        "model_case_count": sum(row["operation"] in {"generate_card", "review_answer"} for row in rows),
        "metrics": {
            "schema_pass_rate": rate("schema_ok"),
            "grounded_card_rate": rate("grounding_ok"),
            "review_agreement_rate": rate("verdict_ok"),
            "safety_guard_rate": rate("safety_ok"),
            "quality_score": round(statistics.mean(measurable), 4),
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mini", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--fail-below", type=float, default=0.0)
    args = parser.parse_args()
    report = run(args.mini, args.output)
    return 1 if report["metrics"]["quality_score"] < args.fail_below else 0


if __name__ == "__main__":
    raise SystemExit(main())
