import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tests.reliability.measure_prod import percentile, write_report


class ReliabilityReportTest(unittest.TestCase):
    def test_percentile_and_report_capture_version_and_uptime(self):
        started = datetime.now(timezone.utc)
        samples = [
            {"at": started.isoformat(), "status": 200, "latency_ms": 10.0, "version": "lab5"},
            {"at": (started + timedelta(seconds=5)).isoformat(), "status": 200, "latency_ms": 20.0, "version": "lab5"},
            {"at": (started + timedelta(seconds=10)).isoformat(), "status": 503, "latency_ms": 3.0, "version": None},
        ]
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "report.json"

            report = write_report(destination, "https://example.test/health", samples, "lab5")

            self.assertEqual(percentile([10.0, 20.0], 0.95), 20.0)
            self.assertEqual(report["uptime_percent"], 66.67)
            self.assertEqual(report["latency_p50_ms"], 15.0)
            self.assertEqual(report["version_match_percent"], 100.0)
            self.assertEqual(json.loads(destination.read_text(encoding="utf-8"))["sample_count"], 3)


if __name__ == "__main__":
    unittest.main()
