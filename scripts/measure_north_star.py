"""Measure North Star exactly as recorded in docs/prd.md.

North Star = share of started external study sessions whose server-side
progress (study_sessions.current_position) reached at least 5 cards.

Input: a sessions export (JSON list) with fields
  user_id, cohort ("external" | "team" | "smoke"), created_at (ISO),
  current_position.
Only cohort == "external" rows are counted; team and smoke traffic is
excluded, as recorded in the PRD.

Usage:
    python scripts/measure_north_star.py \
        artifacts/product/north-star-sessions-export.json \
        artifacts/product/north-star-measurement.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

TARGET = 0.70
MIN_CONFIRMED_SAMPLE = 10
REACH_POSITION = 5


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def main() -> int:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("artifacts/product/north-star-sessions-export.json")
    target_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("artifacts/product/north-star-measurement.json")

    sessions = json.loads(source.read_text(encoding="utf-8"))
    external = [row for row in sessions if row.get("cohort") == "external"]
    started = len(external)
    reached = sum(1 for row in external if int(row.get("current_position", 0)) >= REACH_POSITION)
    actual = (reached / started) if started else 0.0
    times = [parse_time(row["created_at"]) for row in external if row.get("created_at")]

    report = {
        "metric": "share_of_started_sessions_reaching_at_least_five_cards",
        "formula": "sessions(current_position >= 5) / sessions(started in period), external cohort only",
        "source_table": "study_sessions",
        "target": TARGET,
        "release": "v0.5.1",
        "period_start": min(times).isoformat() if times else None,
        "period_end": max(times).isoformat() if times else None,
        "measurement_method": "study_sessions export (PRD method); team and smoke cohorts excluded",
        "sessions_export": str(source).replace("\\", "/"),
        "started_sessions": started,
        "sessions_reaching_five_cards": reached,
        "actual": round(actual, 4),
        "delta_to_target_pp": round((actual - TARGET) * 100, 2),
        "target_met_on_observed_sample": bool(started and actual >= TARGET),
        "statistically_confirmed": bool(started >= MIN_CONFIRMED_SAMPLE and actual >= TARGET),
        "evidence": sorted({ref for row in external for ref in row.get("evidence", [])}),
        "limitation": (
            f"n={started}; at least {MIN_CONFIRMED_SAMPLE} external sessions are required "
            "before claiming Demo Day confirmation (>=7/10)"
        ),
    }
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
