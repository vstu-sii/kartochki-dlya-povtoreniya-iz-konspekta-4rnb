"""Reproducible, provider-free evaluation of the read-only source lookup tool."""

import argparse
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from ml.tools.source_lookup import SourceLookupRequest, SourceLookupTool


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT / "tests/evals/retrieval-cases.jsonl"
DEFAULT_OUTPUT = ROOT / "artifacts/experiments/lab4-retrieval-results.json"


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * fraction))]


def run(dataset: Path) -> dict:
    cases = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    tool = SourceLookupTool(timeout_seconds=1.0)
    rows: list[dict] = []
    latencies: list[float] = []
    reciprocal_ranks: list[float] = []
    for case in cases:
        started = time.perf_counter()
        result = tool.run(
            SourceLookupRequest(
                user_id="eval-user",
                resource_owner_id="eval-user",
                query=case["query"],
                pages=case["pages"],
                max_results=3,
            )
        )
        latency_ms = round((time.perf_counter() - started) * 1000, 3)
        latencies.append(latency_ms)
        pages = [item["page"] for item in result.passages]
        rank = pages.index(case["expected_page"]) + 1 if case["expected_page"] in pages else None
        reciprocal_ranks.append(1 / rank if rank else 0.0)
        rows.append(
            {
                "id": case["id"],
                "expected_page": case["expected_page"],
                "returned_pages": pages,
                "rank": rank,
                "hit_at_1": rank == 1,
                "recall_at_3": rank is not None and rank <= 3,
                "latency_ms": latency_ms,
                "status": result.status,
            }
        )
    count = len(rows)
    return {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "suite": "source-lookup-retrieval",
        "dataset": str(dataset.relative_to(ROOT)).replace("\\", "/"),
        "case_count": count,
        "metrics": {
            "hit_rate_at_1": round(sum(row["hit_at_1"] for row in rows) / count, 4),
            "recall_at_3": round(sum(row["recall_at_3"] for row in rows) / count, 4),
            "mrr": round(statistics.mean(reciprocal_ranks), 4),
            "latency_p50_ms": percentile(latencies, 0.50),
            "latency_p95_ms": percentile(latencies, 0.95),
        },
        "cases": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--min-hit-at-1", type=float, default=0.0)
    parser.add_argument("--min-recall-at-3", type=float, default=0.0)
    args = parser.parse_args()
    report = run(args.dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["metrics"], ensure_ascii=False))
    metrics = report["metrics"]
    return int(metrics["hit_rate_at_1"] < args.min_hit_at_1 or metrics["recall_at_3"] < args.min_recall_at_3)


if __name__ == "__main__":
    raise SystemExit(main())
