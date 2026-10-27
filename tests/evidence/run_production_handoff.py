"""Run and record a provider-only PDF -> cards -> five reviews scenario."""
from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[2]


def percentile_nearest_rank(values: list[int], percentile: float) -> int:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(percentile * len(ordered)) - 1)]


def request_json(client: httpx.Client, method: str, url: str, **kwargs) -> tuple[int, int, dict]:
    started = time.perf_counter()
    response = client.request(method, url, **kwargs)
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    try:
        body = response.json()
    except ValueError:
        body = {"raw_preview": response.text[:300]}
    return response.status_code, elapsed_ms, body


def assert_provider_call(body: dict, label: str) -> None:
    if body.get("fallback_used") is not False:
        raise RuntimeError(f"{label}: fallback_used={body.get('fallback_used')!r}, reason={body.get('fallback_reason')!r}")
    if body.get("fallback_reason") not in (None, ""):
        raise RuntimeError(f"{label}: fallback_reason={body.get('fallback_reason')!r}")
    if "gemini" not in str(body.get("model", "")).lower():
        raise RuntimeError(f"{label}: non-Gemini model {body.get('model')!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--scenarios", type=int, default=5)
    parser.add_argument("--fixture", choices=("alternating", "ordinary", "formula"), default="alternating")
    parser.add_argument("--card-count", type=int, choices=range(5, 11), help="Set requested count for each scenario")
    parser.add_argument("--input-usd-per-million", type=float, default=0.30)
    parser.add_argument("--output-usd-per-million", type=float, default=2.50)
    parser.add_argument("--budget-usd", type=float, default=0.04)
    parser.add_argument("--delay-seconds", type=float, default=0.0, help="Delay between provider calls to respect rate limits")
    parser.add_argument("--allow-fallback", action="store_true", help="Record degraded-path diagnostics; never report these as a provider-only run")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    base = args.base_url.rstrip("/")
    fixtures = [
        ROOT / "tests/fixtures/lab5-devops-source.pdf",
        ROOT / "tests/fixtures/lab5-formulas-source.pdf",
    ]
    if args.fixture == "ordinary":
        fixtures = fixtures[:1]
    elif args.fixture == "formula":
        fixtures = fixtures[1:]
    if any(not path.exists() for path in fixtures):
        raise SystemExit("Lab5 PDF fixtures are missing")

    report: dict = {
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base,
        "method": "fallback-enabled diagnostic; nearest-rank timings" if args.allow_fallback else "provider-only full scenarios; nearest-rank p95",
        "scenario_count": args.scenarios,
        "prices_usd_per_million_tokens": {
            "input": args.input_usd_per_million,
            "output": args.output_usd_per_million,
        },
        "budget_usd_per_scenario": args.budget_usd,
        "cost_note": "Paid-tier estimate from exposed provider counts; actual free-tier charges and provider billing are not inferred. Confirm the deployed revision includes thinking-token accounting.",
        "pricing_source": "https://ai.google.dev/gemini-api/docs/pricing",
        "health": {},
        "scenarios": [],
    }

    try:
        with httpx.Client(timeout=150.0, follow_redirects=True) as client:
            status, elapsed, health = request_json(client, "GET", f"{base}/health")
            report["health"] = {"status": status, "elapsed_ms": elapsed, "body": health}
            if status != 200:
                raise RuntimeError(f"health returned HTTP {status}")

            for index in range(args.scenarios):
                fixture = fixtures[index % len(fixtures)]
                user_id = f"quality-final-{int(time.time())}-{index + 1}"
                requested_count = args.card_count or 5 + (index % 5)
                with fixture.open("rb") as source:
                    status, elapsed, generated = request_json(
                        client,
                        "POST",
                        f"{base}/v1/ai/card-sets/from-pdf",
                        headers={"X-User-ID": user_id},
                        files={"file": (fixture.name, source, "application/pdf")},
                        data={"requested_card_count": str(requested_count), "language": "ru"},
                    )
                current = {"number":index+1,"fixture":fixture.name,"user_alias":user_id,
                           "generation":{"status":status,"wall_ms":elapsed,"response":generated},
                           "reviews":[],"status":"generation_received","answer_mode":"reference_copy_not_paraphrase"}
                report["scenarios"].append(current)
                report["status"]="in_progress"
                output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
                if status != 201:
                    raise RuntimeError(f"scenario {index + 1}: PDF generation HTTP {status}: {generated}")
                if not args.allow_fallback:
                    assert_provider_call(generated, f"scenario {index + 1} generation")

                status_session, elapsed_session, session = request_json(
                    client,
                    "POST",
                    f"{base}/v1/ai/sessions",
                    json={"card_set_id": generated["card_set_id"], "user_id": user_id},
                )
                if status_session != 201:
                    raise RuntimeError(f"scenario {index + 1}: session HTTP {status_session}: {session}")

                reviews = current["reviews"]
                if not generated.get("cards"):
                    raise RuntimeError(f"scenario {index + 1}: no cards generated")
                for card_index in range(1, 6):
                    card = generated["cards"][(card_index - 1) % len(generated["cards"])]
                    if args.delay_seconds:
                        time.sleep(args.delay_seconds)
                    student_answer = card["reference_answer"]
                    review_status, review_elapsed, review = request_json(
                        client,
                        "POST",
                        f"{base}/v1/ai/answer-reviews",
                        headers={"X-User-ID": user_id},
                        json={
                            "session_id": session["session_id"],
                            "card": card,
                            "student_answer": student_answer,
                        },
                    )
                    reviews.append({"status": review_status, "wall_ms": review_elapsed, "response": review,
                                    "student_answer":student_answer,"answer_mode":"reference_copy_not_paraphrase"})
                    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
                    if review_status != 200:
                        raise RuntimeError(f"scenario {index + 1} review {card_index}: HTTP {review_status}: {review}")
                    if not args.allow_fallback:
                        assert_provider_call(review, f"scenario {index + 1} review {card_index}")
                    if review.get("persisted") is not True or not review.get("review_id"):
                        raise RuntimeError(f"scenario {index + 1} review {card_index}: persistence not acknowledged")


                reopen_status, reopen_elapsed, reopened = request_json(
                    client,
                    "GET",
                    f"{base}/v1/ai/sessions/{session['session_id']}",
                    headers={"X-User-ID": user_id},
                )
                if reopen_status != 200 or len(reopened.get("cards", [])) != len(generated["cards"]):
                    raise RuntimeError(f"scenario {index + 1}: persisted cards did not reopen: {reopened}")

                calls = [generated, *(item["response"] for item in reviews)]
                input_tokens = sum(int(item.get("usage", {}).get("input_tokens", 0)) for item in calls)
                output_tokens = sum(int(item.get("usage", {}).get("output_tokens", 0)) for item in calls)
                provider_only = all(call.get("fallback_used") is False and "gemini" in str(call.get("model", "")).lower() for call in calls)
                cost = (input_tokens * args.input_usd_per_million / 1_000_000 + output_tokens * args.output_usd_per_million / 1_000_000) if provider_only else None
                current.update(
                    {
                        "status":"completed",
                        "number": index + 1,
                        "fixture": fixture.name,
                        "user_alias": user_id,
                        "generation": {"status": status, "wall_ms": elapsed, "response": generated},
                        "session": {"status": status_session, "wall_ms": elapsed_session, "response": session},
                        "reviews": reviews,
                        "reopen": {"status": reopen_status, "wall_ms": reopen_elapsed, "card_count": len(reopened.get("cards", []))},
                        "totals": {
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "cost_usd": round(cost, 8) if cost is not None else None,
                            "within_budget": cost <= args.budget_usd if cost is not None else None,
                            "usage_note": "provider usage" if provider_only else "mixed/fallback usage; not provider billing evidence",
                        },
                    }
                )
                # Preserve completed real scenarios if a later request fails.
                report["status"] = "in_progress"
                output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                if args.delay_seconds and index + 1 < args.scenarios:
                    time.sleep(args.delay_seconds)
    except (RuntimeError, httpx.HTTPError) as exc:
        report["status"]="failed"
        report["failure"]={"type":type(exc).__name__,"message":str(exc)[:500]}
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("Measurement failed; raw partial responses preserved at "+str(output))
        return 1

    generation_latencies = [item["generation"]["wall_ms"] for item in report["scenarios"]]
    review_latencies = [review["wall_ms"] for item in report["scenarios"] for review in item["reviews"]]
    report["summary"] = {
        "all_provider_calls_without_fallback": all(
            call.get("fallback_used") is False and "gemini" in str(call.get("model", "")).lower()
            for item in report["scenarios"]
            for call in [item["generation"]["response"], *(review["response"] for review in item["reviews"])]
        ),
        "generation_p50_wall_ms": round(statistics.median(generation_latencies)),
        "generation_p95_wall_ms": percentile_nearest_rank(generation_latencies, 0.95),
        "review_p50_wall_ms": round(statistics.median(review_latencies)),
        "review_p95_wall_ms": percentile_nearest_rank(review_latencies, 0.95),
        "p95_method": "nearest-rank, wall-clock latency",
        "generation_sample_size": len(generation_latencies),
        "review_sample_size": len(review_latencies),
        "total_input_tokens": sum(item["totals"]["input_tokens"] for item in report["scenarios"]),
        "total_output_tokens": sum(item["totals"]["output_tokens"] for item in report["scenarios"]),
        "total_cost_usd": round(sum(item["totals"]["cost_usd"] for item in report["scenarios"]), 8) if all(item["totals"]["cost_usd"] is not None for item in report["scenarios"]) else None,
    }
    report["status"] = "completed"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
