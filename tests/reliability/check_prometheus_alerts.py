"""Fail when Prometheus reports active alerts after the staging contour starts."""

import argparse
import json
import urllib.request
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:9090/api/v1/alerts")
    parser.add_argument("--output", default="artifacts/reliability/staging-alerts.json")
    args = parser.parse_args()

    with urllib.request.urlopen(args.url, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    alerts = payload.get("data", {}).get("alerts", [])
    active = [alert for alert in alerts if alert.get("state") in {"pending", "firing"}]
    report = {
        "prometheus_url": args.url,
        "active_alert_count": len(active),
        "active_alerts": active,
        "result": "pass" if not active else "fail",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if not active else 1


if __name__ == "__main__":
    raise SystemExit(main())
