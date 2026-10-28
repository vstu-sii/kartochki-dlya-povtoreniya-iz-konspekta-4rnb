"""Reproducible step-load runner using only the standard library."""
import argparse, concurrent.futures, json, statistics, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

def one(url, timeout):
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            response.read(); status = response.status
    except Exception:
        status = 0
    return status, (time.perf_counter() - started) * 1000

def main():
    p = argparse.ArgumentParser(); p.add_argument("--base-url", required=True); p.add_argument("--path", default="/health")
    p.add_argument("--levels", default="1,5,10,20,40"); p.add_argument("--requests-per-level", type=int, default=20)
    p.add_argument("--timeout", type=float, default=10); p.add_argument("--p95-limit-ms", type=float, default=2000)
    p.add_argument("--max-error-rate", type=float, default=.01); p.add_argument("--output", default="artifacts/load/lab5-load-results.json")
    a = p.parse_args(); url = a.base_url.rstrip("/") + "/" + a.path.lstrip("/"); rows = []
    for workers in map(int, a.levels.split(",")):
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(lambda _: one(url, a.timeout), range(a.requests_per_level)))
        values = sorted(latency for _, latency in results); errors = sum(not 200 <= status < 400 for status, _ in results)
        row = {"concurrency": workers, "requests": len(results), "errors": errors, "error_rate": errors / len(results),
               "latency_p50_ms": round(statistics.median(values), 2), "latency_p95_ms": round(values[min(len(values)-1, int(len(values)*.95))], 2)}
        row["within_slo"] = row["error_rate"] <= a.max_error_rate and row["latency_p95_ms"] <= a.p95_limit_ms
        rows.append(row); print(json.dumps(row))
    good = [r["concurrency"] for r in rows if r["within_slo"]]; bad = [r["concurrency"] for r in rows if not r["within_slo"]]
    report = {"run_at": datetime.now(timezone.utc).isoformat(), "target": url,
              "slo": {"p95_ms": a.p95_limit_ms, "max_error_rate": a.max_error_rate}, "levels": rows,
              "verified_sustainable_concurrency": max(good, default=0), "first_failed_concurrency": min(bad, default=None),
              "limit_interpretation": "first failed step" if bad else "not reached; lower bound only"}
    out = Path(a.output); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return 0

if __name__ == "__main__": raise SystemExit(main())
