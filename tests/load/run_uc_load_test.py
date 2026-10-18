"""Find the sustainable concurrency limit of the real UC-01 generation path."""

import argparse
import json
import math
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, request
from uuid import uuid4


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1)]


def one_call(base_url: str, ordinal: int, timeout: float) -> dict:
    suffix = uuid4().hex[:12]
    payload = json.dumps({
        "document_id": f"load_{suffix}",
        "language": "ru",
        "requested_card_count": 5,
        "pages": [{"page": 1, "text": "Распределенная система хранит данные в нескольких узлах. Репликация создаёт копии данных. Кворум согласует чтение и запись. Таймаут ограничивает ожидание ответа. Повторный запрос обрабатывает временный отказ."}],
    }, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        f"{base_url.rstrip('/')}/v1/ai/card-sets",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json", "X-User-ID": f"load-user-{suffix}", "Idempotency-Key": f"load-{ordinal}-{suffix}"},
    )
    started = time.perf_counter()
    try:
        with request.urlopen(req, timeout=timeout) as response:
            body = json.loads(response.read())
            status = response.status
            ok = status == 201 and len(body.get("cards", [])) >= 5
            reason = None if ok else "invalid_response"
    except error.HTTPError as exc:
        status, ok, reason = exc.code, False, f"http_{exc.code}"
    except Exception as exc:  # noqa: BLE001 - failure type is part of the measurement
        status, ok, reason = 0, False, type(exc).__name__
    return {"status": status, "ok": ok, "reason": reason, "latency_ms": round((time.perf_counter() - started) * 1000, 2)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8095")
    parser.add_argument("--levels", default="1,5,10,20,40,80")
    parser.add_argument("--requests-per-level", type=int, default=40)
    parser.add_argument("--p95-limit-ms", type=float, default=500.0)
    parser.add_argument("--error-limit", type=float, default=0.01)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--output", default="artifacts/load/lab5-uc-load-results.json")
    args = parser.parse_args()
    levels = [int(item) for item in args.levels.split(",")]
    results = []
    for level in levels:
        with ThreadPoolExecutor(max_workers=level) as pool:
            samples = list(pool.map(lambda i: one_call(args.base_url, i, args.timeout), range(args.requests_per_level)))
        latencies = [sample["latency_ms"] for sample in samples]
        error_rate = sum(not sample["ok"] for sample in samples) / len(samples)
        passed = error_rate <= args.error_limit and percentile(latencies, 0.95) <= args.p95_limit_ms
        results.append({
            "concurrency": level,
            "requests": len(samples),
            "successes": sum(sample["ok"] for sample in samples),
            "error_rate": round(error_rate, 4),
            "p50_ms": round(statistics.median(latencies), 2),
            "p95_ms": round(percentile(latencies, 0.95), 2),
            "passed_slo": passed,
            "failures": [sample for sample in samples if not sample["ok"]][:10],
        })
        if not passed:
            break
    passed_levels = [row["concurrency"] for row in results if row["passed_slo"]]
    failed_levels = [row["concurrency"] for row in results if not row["passed_slo"]]
    artifact = {
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "scenario": "UC-01: UI/API generation path with model and database persistence",
        "base_url": args.base_url,
        "slo": {"error_rate_lte": args.error_limit, "p95_ms_lte": args.p95_limit_ms},
        "verified_sustainable_concurrency": max(passed_levels) if passed_levels else 0,
        "first_failed_concurrency": failed_levels[0] if failed_levels else None,
        "levels": results,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
