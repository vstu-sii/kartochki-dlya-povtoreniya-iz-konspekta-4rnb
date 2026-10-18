"""Reproducible, provider-free evaluation of the read-only source lookup tool."""

import argparse
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from ml.models.baseline import BaselineModel
from ml.tools.source_lookup import SourceLookupRequest, SourceLookupTool, build_retrieval_query


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT / "tests/evals/retrieval-cases.jsonl"
DEFAULT_OUTPUT = ROOT / "artifacts/experiments/lab4-retrieval-results.json"


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * fraction))]


def _metrics(rows: list[dict], latencies: list[float], reciprocal_ranks: list[float]) -> dict:
    count = len(rows)
    return {
        "hit_rate_at_1": round(sum(row["hit_at_1"] for row in rows) / count, 4),
        "recall_at_3": round(sum(row["recall_at_3"] for row in rows) / count, 4),
        "mrr": round(statistics.mean(reciprocal_ranks), 4),
        "latency_p50_ms": percentile(latencies, 0.50),
        "latency_p95_ms": percentile(latencies, 0.95),
    }


def _evaluate(tool: SourceLookupTool, cases: list[dict], query_mode: str) -> tuple[list[dict], dict]:
    rows: list[dict] = []
    latencies: list[float] = []
    reciprocal_ranks: list[float] = []
    for case in cases:
        query = case["query"] if query_mode == "curated" else build_retrieval_query(case["pages"])
        started = time.perf_counter()
        result = tool.run(SourceLookupRequest("eval-user", "eval-user", query, case["pages"], 3))
        latency_ms = round((time.perf_counter() - started) * 1000, 3)
        latencies.append(latency_ms)
        pages = [item["page"] for item in result.passages]
        rank = pages.index(case["expected_page"]) + 1 if case["expected_page"] in pages else None
        reciprocal_ranks.append(1 / rank if rank else 0.0)
        rows.append({"id": case["id"], "query_mode": query_mode, "expected_page": case["expected_page"],
                     "returned_pages": pages, "rank": rank, "hit_at_1": rank == 1,
                     "recall_at_3": rank is not None and rank <= 3, "latency_ms": latency_ms,
                     "status": result.status})
    return rows, _metrics(rows, latencies, reciprocal_ranks)


def _coverage_probe(tool: SourceLookupTool) -> dict:
    pages = [
        {"page": index, "text": f"Раздел {index}. Основной учебный факт номер {index}."}
        for index in range(1, 6)
    ]
    result = tool.run(SourceLookupRequest("eval-user", "eval-user", build_retrieval_query(pages), pages, 3))
    returned = [item["page"] for item in result.passages]
    return {"page_count": len(pages), "max_results": 3, "returned_pages": returned,
            "dropped_pages": [page["page"] for page in pages if page["page"] not in returned],
            "all_document_facts_preserved": len(returned) == len(pages)}


def run(dataset: Path) -> dict:
    cases = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    tool = SourceLookupTool(timeout_seconds=1.0)
    curated_rows, curated_metrics = _evaluate(tool, cases, "curated")
    pipeline_rows, pipeline_metrics = _evaluate(tool, cases, "production-query-builder")
    model = BaselineModel()
    e2e_rows = []
    for case in cases:
        response = model.generate({"user_id": "eval-user", "resource_owner_id": "eval-user",
                                   "pages": case["pages"], "requested_card_count": 3})
        e2e_rows.append({"id": case["id"], "card_count": len(response["cards"]),
                         "card_source_pages": sorted({card["source_page"] for card in response["cards"]}),
                         "tool_status": response["tool_status"]})
    return {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "suite": "source-lookup-retrieval",
        "dataset": str(dataset.relative_to(ROOT)).replace("\\", "/"),
        "case_count": len(cases),
        "metrics": curated_metrics,
        "curated_query": {"metrics": curated_metrics, "cases": curated_rows},
        "production_query_builder": {"metrics": pipeline_metrics, "cases": pipeline_rows},
        "end_to_end": {"path": "pages -> production query -> top-3 fragments -> deterministic cards",
                       "cases": e2e_rows},
        "top3_coverage_probe": _coverage_probe(tool),
        "limitations": [
            "Ten synthetic retrieval cases do not estimate whole-product quality.",
            "Top-3 retrieval necessarily drops document sections when more than three pages are relevant.",
        ],
        "cases": curated_rows,
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
    pipeline = report["production_query_builder"]["metrics"]
    return int(
        metrics["hit_rate_at_1"] < args.min_hit_at_1
        or metrics["recall_at_3"] < args.min_recall_at_3
        or pipeline["recall_at_3"] < args.min_recall_at_3
    )


if __name__ == "__main__":
    raise SystemExit(main())
