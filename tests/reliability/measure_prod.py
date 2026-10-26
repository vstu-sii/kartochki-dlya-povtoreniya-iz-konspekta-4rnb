"""Sample a public health endpoint and save raw evidence plus SLO metrics."""

import argparse
import json
import statistics
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(len(ordered) * fraction))], 2)


def write_report(path: Path, target: str, samples: list[dict], expected_version: str) -> dict:
    successful = [x for x in samples if 200 <= x["status"] < 400]
    latencies = [x["latency_ms"] for x in successful]
    version_matches = sum(x.get("version") == expected_version for x in successful) if expected_version else len(successful)
    report = {
        "target": target,
        "sample_count": len(samples),
        "period_start": samples[0]["at"],
        "period_end": samples[-1]["at"],
        "observation_duration_seconds": round(
            (datetime.fromisoformat(samples[-1]["at"]) - datetime.fromisoformat(samples[0]["at"])).total_seconds(), 2
        ),
        "successful_samples": len(successful),
        "uptime_percent": round(len(successful) / len(samples) * 100, 2),
        "latency_p50_ms": round(statistics.median(latencies), 2) if latencies else None,
        "latency_p95_ms": percentile(latencies, 0.95),
        "expected_version": expected_version or None,
        "version_match_percent": round(version_matches / len(successful) * 100, 2) if successful else 0.0,
        "method": "active HTTP health sampling; latency is calculated from successful responses",
        "samples": samples,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--interval", type=float, default=1)
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--min-uptime", type=float, default=99)
    parser.add_argument("--expected-version", default="")
    parser.add_argument("--output", default="artifacts/reliability/prod-window.json")
    args = parser.parse_args()
    if args.samples < 1 or args.interval < 0 or not 0 <= args.min_uptime <= 100:
        parser.error("samples must be positive, interval non-negative and min-uptime in 0..100")

    output = Path(args.output)
    samples: list[dict] = []
    report: dict = {}
    for index in range(args.samples):
        started = time.perf_counter()
        observation = {
            "at": datetime.now(timezone.utc).isoformat(),
            "status": 0,
            "latency_ms": 0.0,
            "version": None,
        }
        try:
            with urllib.request.urlopen(args.url, timeout=args.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
                observation["status"] = response.status
                observation["version"] = body.get("version")
        except Exception as error:  # store only the type, never response content or credentials
            observation["error"] = type(error).__name__
        observation["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
        samples.append(observation)
        report = write_report(output, args.url, samples, args.expected_version)
        if index + 1 < args.samples:
            time.sleep(args.interval)

    summary = {key: value for key, value in report.items() if key != "samples"}
    print(json.dumps(summary, ensure_ascii=False))
    uptime_ok = report["uptime_percent"] >= args.min_uptime
    version_ok = not args.expected_version or report["version_match_percent"] == 100.0
    return 0 if uptime_ok and version_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
