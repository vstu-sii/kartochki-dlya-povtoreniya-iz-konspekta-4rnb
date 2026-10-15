"""Reproducible before/after security attack runner."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.guards import inspect_untrusted_text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("before", "after"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).with_name("attacks.jsonl")
    cases = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = []
    for case in cases:
        if args.mode == "before":
            actual = "allow"  # Lab3 guard checked size/MIME, not injection content.
        else:
            actual = "allow" if inspect_untrusted_text(case["text"]).allowed else "block"
        expected = case[f"expected_{args.mode}"]
        rows.append({"id": case["id"], "point": case["point"], "expected": expected, "actual": actual, "passed": actual == expected})
    result = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "case_count": len(rows),
        "passed": sum(row["passed"] for row in rows),
        "failed": sum(not row["passed"] for row in rows),
        "cases": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
