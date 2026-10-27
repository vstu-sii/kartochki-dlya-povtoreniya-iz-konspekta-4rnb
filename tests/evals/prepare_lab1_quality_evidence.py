"""Prepare raw AI evidence requested for the Lab 1 acceptance review.

The script intentionally does not invent human judgements, PDF counts, live
latencies, or provider billing.  It creates 20 reproducible answer-review rows
and leaves the fields that must be measured jointly with Quality explicitly
empty.
"""

import argparse
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ml.models.baseline import BaselineModel  # noqa: E402
from tests.evals.dataset_catalog import dataset_hash, load_dataset  # noqa: E402


DEFAULT_OUTPUT = ROOT / "artifacts/evals/lab1-ai-quality-evidence.json"


class SilentEvidenceTrace:
    """The evidence JSON is the trace for this offline preparation command."""

    def record(self, *args, **kwargs) -> None:
        return None


def git_metadata() -> dict:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.strip()
        return {"git_sha": commit, "working_tree_clean": not bool(status)}
    except (OSError, subprocess.CalledProcessError):
        return {"git_sha": None, "working_tree_clean": None}


def nearest_rank(values: list[int | float], quantile: float) -> int | float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(quantile * len(ordered)) - 1)]


def summarize_existing(report: dict) -> dict:
    """Calculate only metrics backed by complete raw measurements."""
    answer = report["answer_review_check"]
    reviews = [row["quality_manual_review"] for row in answer["rows"]]
    boolean_fields = (
        "no_contradiction",
        "mandatory_points_complete",
        "critical_tone_violation",
        "minor_tone_violation",
    )
    if all(isinstance(review.get(field), bool) for review in reviews for field in boolean_fields):
        count = len(reviews)
        answer["metrics"] = {
            "no_contradiction_rate": round(sum(row["no_contradiction"] for row in reviews) / count, 4),
            "mandatory_points_complete_rate": round(sum(row["mandatory_points_complete"] for row in reviews) / count, 4),
            "critical_tone_violations": sum(row["critical_tone_violation"] for row in reviews),
            "minor_tone_violation_rate": round(sum(row["minor_tone_violation"] for row in reviews) / count, 4),
        }
        answer["status"] = "complete_joint_manual_review"

    thesis = report["pdf_thesis_check"]
    thesis_rows = [row for document in thesis["documents"] for row in document.get("theses", [])]
    if thesis_rows and all(isinstance(row.get("correct"), bool) for row in thesis_rows):
        correct = sum(row["correct"] for row in thesis_rows)
        thesis.update(
            status="complete_manual_review",
            checked_theses=len(thesis_rows),
            correct_theses=correct,
            accuracy=round(correct / len(thesis_rows), 4),
        )

    formulas = report["formula_extraction_check"]
    formula_documents = formulas["documents"]
    if formula_documents and all(
        isinstance(row.get("source_formula_count"), int)
        and isinstance(row.get("extracted_formula_count"), int)
        and 0 <= row["extracted_formula_count"] <= row["source_formula_count"]
        for row in formula_documents
    ):
        source_count = sum(row["source_formula_count"] for row in formula_documents)
        extracted_count = sum(row["extracted_formula_count"] for row in formula_documents)
        if source_count > 0:
            formulas.update(
                status="complete_manual_counts",
                source_formula_count=source_count,
                extracted_formula_count=extracted_count,
                lost_formula_count=source_count - extracted_count,
                loss_rate=round((source_count - extracted_count) / source_count, 4),
            )

    cost = report["scenario_cost_check"]
    scenario = cost["full_scenario"]
    cost_fields = (
        "input_tokens",
        "output_tokens",
        "input_price_usd_per_million",
        "output_price_usd_per_million",
    )
    if scenario.get("model") and all(isinstance(scenario.get(field), (int, float)) for field in cost_fields):
        scenario["calculated_cost_usd"] = round(
            scenario["input_tokens"] / 1_000_000 * scenario["input_price_usd_per_million"]
            + scenario["output_tokens"] / 1_000_000 * scenario["output_price_usd_per_million"],
            8,
        )
        scenario["token_delta_vs_lab1_budget"] = (
            scenario["input_tokens"] + scenario["output_tokens"] - cost["lab1_budget"]["planned_total_tokens"]
        )
        cost["status"] = "complete_full_live_scenario"

    latency = report["live_latency_check"]
    pdf_runs = latency["pdf_to_cards_runs_ms"]
    review_runs = latency["answer_to_review_runs_ms"]
    if (
        pdf_runs
        and review_runs
        and latency.get("version_or_git_sha")
        and latency.get("environment")
        and latency.get("model")
    ):
        latency["pdf_to_cards_run_count"] = len(pdf_runs)
        latency["answer_to_review_run_count"] = len(review_runs)
        latency["pdf_to_cards_p95_ms"] = nearest_rank(pdf_runs, 0.95)
        latency["answer_to_review_p95_ms"] = nearest_rank(review_runs, 0.95)
        latency["status"] = "complete_live_measurement"
    return report


def review_payload(case: dict) -> dict:
    source = case["context"][0]
    return {
        "session_id": "lab1_quality_review",
        "card": {
            "card_id": case["id"].lower(),
            "question": case["input"]["question"],
            "reference_answer": case["input"]["reference_answer"],
            "source_page": source["page"],
            "source_quote": source["text"],
            "difficulty": "basic",
        },
        "student_answer": case["input"]["student_answer"],
    }


def build_answer_rows(count: int) -> tuple[list[dict], dict]:
    cases = [case for case in load_dataset() if case["operation"] == "review_answer"][:count]
    if len(cases) != count:
        raise ValueError(f"Need {count} review cases, dataset contains only {len(cases)}")

    model = BaselineModel(SilentEvidenceTrace())
    rows = []
    input_tokens = output_tokens = 0
    models = set()
    for case in cases:
        result = model.review(review_payload(case))
        usage = result.get("usage", {})
        input_tokens += int(usage.get("input_tokens", 0))
        output_tokens += int(usage.get("output_tokens", 0))
        models.add(result.get("model", "unknown"))
        rows.append(
            {
                "case_id": case["id"],
                "question": case["input"]["question"],
                "student_answer": case["input"]["student_answer"],
                "reference_answer": case["input"]["reference_answer"],
                "source_context": case["context"],
                "mandatory_points": case["expected_output"].get("required_feedback_points", []),
                "expected_verdict": case["expected_output"]["verdict"],
                "system_result": {
                    "review_id": result["review_id"],
                    "verdict": result["verdict"],
                    "score": result["score"],
                    "feedback": result["feedback"],
                    "missing_points": result.get("missing_points", []),
                    "model": result["model"],
                    "prompt_version": result["prompt_version"],
                    "fallback_used": result["fallback_used"],
                    "trace_id": result["trace_id"],
                    "latency_ms": result["latency_ms"],
                    "usage": usage,
                },
                "quality_manual_review": {
                    "no_contradiction": None,
                    "mandatory_points_complete": None,
                    "critical_tone_violation": None,
                    "minor_tone_violation": None,
                    "reviewer": None,
                    "comment": None,
                },
            }
        )
    return rows, {
        "scope": "20 answer-review calls only; not a complete PDF-to-session scenario",
        "models": sorted(models),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def build_report(count: int) -> dict:
    rows, subset_usage = build_answer_rows(count)
    automatic_matches = sum(row["system_result"]["verdict"] == row["expected_verdict"] for row in rows)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "tests/evals/prepare_lab1_quality_evidence.py",
        "generation_command": "py -3 -m tests.evals.prepare_lab1_quality_evidence --output artifacts/evals/lab1-ai-quality-evidence-after-fix.json",
        "source_revision": git_metadata(),
        "dataset_sha256": dataset_hash(),
        "measurement_rules": {
            "thesis_accuracy": "correct_theses / checked_theses; target >= 0.75",
            "no_contradiction_rate": "rows marked no_contradiction=true / 20; target >= 0.90",
            "mandatory_points_complete_rate": "rows marked mandatory_points_complete=true / 20; target >= 0.80",
            "critical_tone_violations": "count true; target = 0",
            "minor_tone_violation_rate": "count true / 20; target <= 0.05",
            "formula_loss_rate": "(source_formula_count - extracted_formula_count) / source_formula_count; target < 0.10",
            "cost_usd": "input_tokens / 1_000_000 * input_price + output_tokens / 1_000_000 * output_price",
            "latency_p95": "nearest-rank p95 over separate live end-to-end runs",
        },
        "pdf_thesis_check": {
            "status": "pending_source_pdfs_and_manual_review",
            "documents": [],
            "checked_theses": None,
            "correct_theses": None,
            "accuracy": None,
            "target": 0.75,
        },
        "answer_review_check": {
            "status": "pending_joint_manual_labels",
            "case_count": len(rows),
            "source": "versioned golden dataset; system outputs regenerated by this script",
            "automatic_verdict_agreement": {
                "matched": automatic_matches,
                "total": len(rows),
                "rate": round(automatic_matches / len(rows), 4),
                "note": "Technical metric only; it does not replace joint manual review.",
            },
            "rows": rows,
            "metrics": {
                "no_contradiction_rate": None,
                "mandatory_points_complete_rate": None,
                "critical_tone_violations": None,
                "minor_tone_violation_rate": None,
            },
            "targets": {
                "no_contradiction_rate_min": 0.90,
                "mandatory_points_complete_rate_min": 0.80,
                "critical_tone_violations_max": 0,
                "minor_tone_violation_rate_max": 0.05,
            },
        },
        "formula_extraction_check": {
            "status": "pending_source_pdfs_and_manual_counts",
            "documents": [],
            "source_formula_count": None,
            "extracted_formula_count": None,
            "lost_formula_count": None,
            "loss_rate": None,
            "target_max_exclusive": 0.10,
        },
        "scenario_cost_check": {
            "status": "pending_full_live_scenario",
            "lab1_budget": {
                "planned_total_tokens": 18500,
                "free_tier_cost_rub": 0,
                "source": "docs/model-candidates.md",
            },
            "available_partial_measurement": subset_usage,
            "full_scenario": {
                "model": None,
                "input_tokens": None,
                "output_tokens": None,
                "input_price_usd_per_million": None,
                "output_price_usd_per_million": None,
                "calculated_cost_usd": None,
            },
        },
        "live_latency_check": {
            "status": "pending_delivery_environment",
            "version_or_git_sha": None,
            "environment": None,
            "model": None,
            "pdf_to_cards_runs_ms": [],
            "answer_to_review_runs_ms": [],
            "targets_ms": {"pdf_to_cards_p95_max_exclusive": 60000, "answer_to_review_p95_max": 7000},
            "note": "Local deterministic model latency is not end-to-end evidence.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--configured-provider",
        action="store_true",
        help="Use MODEL_PROVIDER from the environment. Default is deterministic and cannot spend quota.",
    )
    parser.add_argument(
        "--summarize-existing",
        action="store_true",
        help="Preserve entered raw measurements and calculate their derived metrics.",
    )
    args = parser.parse_args()
    if args.summarize_existing:
        if not args.output.exists():
            raise SystemExit(f"Evidence file does not exist: {args.output}")
        report = summarize_existing(json.loads(args.output.read_text(encoding="utf-8")))
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"output": str(args.output), "status": "summarized"}, ensure_ascii=False))
        return 0
    if args.count != 20:
        raise SystemExit("Quality acceptance requires exactly 20 answer reviews")
    if not args.configured_provider:
        os.environ["MODEL_PROVIDER"] = "deterministic"
    report = build_report(args.count)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "answer_rows": args.count, "status": "prepared"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
