"""Rehearse the Lab 6 model fallback and validate the local video backup."""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def rehearse(public_url: str | None = None) -> dict:
    # Import after configuring the provider so the scenario matches production.
    os.environ["MODEL_PROVIDER"] = "gemini"
    os.environ["GEMINI_API_KEY"] = "demo-invalid-key-never-sent"
    from ml.models.baseline import BaselineModel

    model = BaselineModel()

    def unavailable(*_args, **_kwargs):
        raise URLError("simulated provider outage")

    model._call_gemini = unavailable
    started = time.perf_counter()
    result = model.generate({
        "document_id": "demo_lab6_document",
        "user_id": "demo_lab6_student",
        "resource_owner_id": "demo_lab6_student",
        "language": "ru",
        "requested_card_count": 5,
        "pages": [{
            "page": 1,
            "text": "Виртуальная память позволяет процессам использовать единое адресное пространство. "
                    "При page fault операционная система загружает отсутствующую страницу с диска. "
                    "Кэш ускоряет повторный доступ к данным.",
        }],
    })
    assert result["fallback_used"] is True
    assert len(result["cards"]) >= 1

    video = ROOT / "docs" / "demo" / "demo-backup.mp4"
    video_ok = video.exists() and video.stat().st_size > 10_000
    if not video_ok:
        raise RuntimeError("video backup is missing or empty")

    production = None
    if public_url:
        with urlopen(public_url.rstrip("/") + "/health", timeout=30) as response:
            production = {"status": response.status, "body": json.load(response)}
        if production["status"] != 200 or production["body"].get("status") != "ok":
            raise RuntimeError("production health check failed")

    report = {
        "status": "passed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider_failure": "simulated URLError before any external request",
        "degradation": {
            "fallback_used": result["fallback_used"],
            "fallback_reason": result["fallback_reason"],
            "cards_returned": len(result["cards"]),
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        },
        "video_backup": {
            "path": "docs/demo/demo-backup.mp4",
            "bytes": video.stat().st_size,
            "readable": video_ok,
        },
        "production": production,
    }
    output = ROOT / "artifacts" / "demo" / "plan-b-rehearsal.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-url", help="Also verify /health of the public production URL")
    args = parser.parse_args()
    print(json.dumps(rehearse(args.public_url), ensure_ascii=False, indent=2))
