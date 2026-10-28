"""Verify a received evidence snapshot without inventing human acceptance."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dataset_catalog import ROOT, dataset_hash, load_dataset

sys.path.insert(0, str(ROOT))


def summarize_manual(rows):
    return {
        "no_contradiction_rate": sum(row["quality_manual_review"]["no_contradiction"] for row in rows) / 20,
        "mandatory_points_complete_rate": sum(row["quality_manual_review"]["mandatory_points_complete"] for row in rows) / 20,
        "critical_tone_violations": sum(row["quality_manual_review"]["critical_tone_violation"] for row in rows),
        "minor_tone_violation_rate": sum(row["quality_manual_review"]["minor_tone_violation"] for row in rows) / 20,
    }


def validate_snapshot(snapshot):
    cases = {case["id"]: case for case in load_dataset()}
    block = snapshot["answer_review_check"]
    rows = block["rows"]
    if len(rows) != 20 or block["case_count"] != 20:
        raise ValueError("Expected exactly 20 answer reviews")
    if len({row["case_id"] for row in rows}) != 20:
        raise ValueError("Duplicate evidence case ID")
    if snapshot["dataset_sha256"] != dataset_hash():
        raise ValueError("Evidence dataset hash differs from this checkout")
    for row in rows:
        case = cases[row["case_id"]]
        expected = case["expected_output"]
        if case["operation"] != "review_answer":
            raise ValueError("Evidence must contain answer-review cases")
        for field in ("question", "student_answer", "reference_answer"):
            if row[field] != case["input"][field]:
                raise ValueError(f"{row['case_id']}: changed {field}")
        for field, value in (
            ("source_context", case["context"]),
            ("mandatory_points", expected["required_feedback_points"]),
            ("expected_verdict", expected["verdict"]),
        ):
            if row[field] != value:
                raise ValueError(f"{row['case_id']}: changed {field}")
    matched = sum(row["system_result"]["verdict"] == row["expected_verdict"] for row in rows)
    actual = {"matched": matched, "total": 20, "rate": matched / 20}
    if any(block["automatic_verdict_agreement"][key] != value for key, value in actual.items()):
        raise ValueError("Claimed verdict agreement does not match the rows")
    fields = ("no_contradiction", "mandatory_points_complete", "critical_tone_violation", "minor_tone_violation")
    completed = 0
    for row in rows:
        labels = row["quality_manual_review"]
        if any(labels.get(key) is not None and type(labels[key]) is not bool for key in fields):
            raise ValueError("Human labels must be booleans or null")
        if all(type(labels.get(key)) is bool for key in fields) and str(labels.get("reviewer") or "").strip():
            completed += 1
    claimed = block.get("metrics", {})
    if any(value is not None for value in claimed.values()):
        if completed != 20 or claimed != summarize_manual(rows):
            raise ValueError("Stored manual metrics do not match 20 completed reviews")
    return rows, actual, completed


def audit(path):
    raw = path.read_bytes()
    snapshot = json.loads(raw.decode("utf-8-sig"))
    rows, agreement, completed = validate_snapshot(snapshot)
    # Force the local provider even if the caller has live Gemini credentials.
    os.environ["MODEL_PROVIDER"] = "deterministic"
    from ml.models.baseline import BaselineModel

    class QuietTrace:
        def record(self, *args, **kwargs):
            pass

    model = BaselineModel(QuietTrace())
    differences = []
    stable_fields = ("verdict", "score", "feedback", "missing_points", "model", "prompt_version", "fallback_used")
    for row in rows:
        context = row["source_context"][0]
        result = model.review({
            "session_id": "lab1-evidence-audit",
            "card": {"card_id": row["case_id"].lower(), "question": row["question"],
                     "reference_answer": row["reference_answer"], "source_page": context["page"],
                     "source_quote": context["text"][:500], "difficulty": "basic"},
            "student_answer": row["student_answer"],
        })
        changed = [key for key in stable_fields if result.get(key) != row["system_result"].get(key)]
        if changed:
            differences.append({"case_id": row["case_id"], "fields": changed})
    manual_metrics = None
    manual_targets_met = None
    if completed == 20:
        manual_metrics = summarize_manual(rows)
        manual_targets_met = {
            "no_contradiction": manual_metrics["no_contradiction_rate"] >= .90,
            "mandatory_points_complete": manual_metrics["mandatory_points_complete_rate"] >= .80,
            "critical_tone": manual_metrics["critical_tone_violations"] == 0,
            "minor_tone": manual_metrics["minor_tone_violation_rate"] <= .05,
        }
    return {
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "audit_kind": "automated_snapshot_audit_not_human_acceptance",
        "checkout_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_snapshot_sha256": hashlib.sha256(raw).hexdigest(),
        "dataset_sha256": dataset_hash(),
        "audit_source_files_sha256": {
            str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (Path(__file__).resolve(), ROOT / "ml/models/baseline.py", *sorted((ROOT / "ml/prompts_v2").glob("*.txt")))
        },
        "snapshot_integrity_verified": True,
        "automatic_verdict_agreement": agreement,
        "stable_output_fields": list(stable_fields),
        "stable_output_matches": 20 - len(differences),
        "differences": differences,
        "excluded_from_exact_comparison": ["latency_ms", "usage", "trace_id", "review_id"],
        "human_review_completed_rows": completed,
        "human_review_ready_for_summary": completed == 20,
        "manual_metrics_from_supplied_labels": manual_metrics,
        "manual_review_targets_met": manual_targets_met,
        "all_manual_review_targets_met": all(manual_targets_met.values()) if manual_targets_met is not None else None,
        "lab1_acceptance_status": "not_established_by_this_automated_audit",
        "limitations": [
            "The supplied snapshot has no original source revision or generator source.",
            "These are REV-001..REV-020 from a synthetic golden set, not a live PDF cohort.",
            "Deterministic usage is a local estimate, not provider billing telemetry.",
            "Verdict agreement does not establish correctness of feedback or golden labels.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "artifacts/evals/lab1-ai-quality-evidence.json")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/evals/lab1-ai-evidence-audit.json")
    args = parser.parse_args()
    try:
        report = audit(args.input)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f"Evidence audit failed: {exc}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["differences"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
