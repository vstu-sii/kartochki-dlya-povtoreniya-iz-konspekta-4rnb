"""Run every Quality suite, preserve failures, and verify unique golden coverage."""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dataset_catalog import ROOT, DATASET_VERSION, dataset_hash, load_dataset


def coverage(model, application, expected_ids):
    model_ids = {r["id"] for r in model["cases"] if r["executed"]}
    app_ids = {r["id"] for r in application["cases"]}
    observed = model_ids | app_ids
    return {"expected": len(expected_ids), "executed_unique": len(observed),
            "missing_ids": sorted(expected_ids - observed), "unexpected_ids": sorted(observed - expected_ids),
            "overlap_ids": sorted(model_ids & app_ids)}


def main():
    output = ROOT / "artifacts/evals/full-suite-results.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    model_path = ROOT / "artifacts/evals/lab4-full-results.json"
    app_path = ROOT / "artifacts/evals/application-results.json"
    suites = [
        ("model-and-guards", ["tests/evals/run_evals.py", "--min-schema", "1", "--min-grounding", "1", "--min-review", ".85", "--min-safety", "1", "--output", str(model_path)], model_path),
        ("application", ["tests/evals/run_application_evals.py"], app_path),
        ("security-before", ["tests/security/run_attacks.py", "--mode", "before", "--output", "artifacts/security/lab4-attacks-before.json"], ROOT / "artifacts/security/lab4-attacks-before.json"),
        ("security-after", ["tests/security/run_attacks.py", "--mode", "after", "--output", "artifacts/security/lab4-attacks-after.json"], ROOT / "artifacts/security/lab4-attacks-after.json"),
        ("retrieval", ["-m", "ml.experiments.run_retrieval_eval", "--min-hit-at-1", ".90", "--min-recall-at-3", "1", "--output", "artifacts/experiments/lab4-retrieval-results.json"], ROOT / "artifacts/experiments/lab4-retrieval-results.json"),
        ("algorithm-regression", ["-m", "ml.experiments.run_ab", "--mode", "algorithm", "--min-b-agreement", ".85", "--fail-on-regression", "--output", "artifacts/experiments/lab4-algorithm-results.json"], ROOT / "artifacts/experiments/lab4-algorithm-results.json"),
        ("prompt-contract", ["-m", "ml.experiments.run_ab", "--mode", "contract", "--output", "artifacts/experiments/lab4-contract-results.json"], ROOT / "artifacts/experiments/lab4-contract-results.json"),
        ("unit-and-integration", ["-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"], None),
    ]
    env = {**os.environ, "MODEL_PROVIDER": "deterministic", "PYTHONUTF8": "1"}
    results = []
    for name, args, report in suites:
        if report:
            report.unlink(missing_ok=True)  # Never reuse a committed stale result after a crash.
        log = ROOT / f"artifacts/evals/{name}.log"
        try:
            with log.open("w", encoding="utf-8") as stream:
                process = subprocess.run([sys.executable, *args], cwd=ROOT, env=env,
                                         stdout=stream, stderr=subprocess.STDOUT, timeout=180)
            code = process.returncode
        except subprocess.TimeoutExpired:
            code = 124
        results.append({"suite": name, "exit_code": code, "report_written": report.exists() if report else None,
                        "log": str(log.relative_to(ROOT)).replace("\\", "/")})
        print(f"{name}: exit {code}", flush=True)
    expected = {case["id"] for case in load_dataset()}
    try:
        counts = coverage(json.loads(model_path.read_text(encoding="utf-8")),
                          json.loads(app_path.read_text(encoding="utf-8")), expected)
    except (OSError, ValueError, KeyError) as exc:
        counts = {"expected": len(expected), "executed_unique": 0, "missing_ids": sorted(expected), "error": str(exc)}
    passed = (all(r["exit_code"] == 0 and r["report_written"] is not False for r in results)
              and not counts["missing_ids"] and not counts.get("unexpected_ids"))
    report = {"run_at": datetime.now(timezone.utc).isoformat(), "dataset_version": DATASET_VERSION,
              "dataset_sha256": dataset_hash(), "passed": passed, "coverage": counts,
              "note": "Coverage is execution, not correctness. No expected-failure waivers.", "suites": results}
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": passed, "coverage": counts}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
