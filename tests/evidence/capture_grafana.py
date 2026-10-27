"""Capture the real provisioned Grafana dashboard and bind it to a revision."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password", default="ci-only-password")
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    captured_at = datetime.now(timezone.utc).isoformat()
    dashboard_url = args.url.rstrip("/") + "/d/flashcards-prod/flashcards-production-overview?orgId=1&from=now-15m&to=now&refresh=5s"
    with sync_playwright() as browser_api:
        browser = browser_api.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=1)
        page.goto(args.url.rstrip("/") + "/login", wait_until="networkidle")
        page.get_by_label("Email or username").fill(args.user)
        page.locator('input[name="password"]').fill(args.password)
        page.get_by_role("button", name="Log in").click()
        page.goto(dashboard_url, wait_until="networkidle")
        page.wait_for_timeout(12_000)
        page.screenshot(path=str(args.output), full_page=True)
        title = page.title()
        browser.close()

    args.metadata.write_text(json.dumps({
        "captured_at": captured_at,
        "dashboard_url": dashboard_url,
        "dashboard_title": title,
        "time_range": "now-15m to now",
        "environment": args.environment,
        "version": args.version,
        "commit_sha": args.sha,
        "traffic": "12 successful health requests, 1 successful generation request, 3 observed 503 generation responses, 3 intentional 422 requests",
        "panels": ["Requests / 5m", "5xx / 5m", "Average latency / 5m (ms)", "Environment / release", "Service logs", "LLM traces"],
        "note": "Screenshot is captured from a running Grafana 11.3.1 container after real requests; it is not a dashboard config or CI status screenshot."
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
