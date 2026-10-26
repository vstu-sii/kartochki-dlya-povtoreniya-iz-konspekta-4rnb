import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Lab6DeliveryTests(unittest.TestCase):
    def test_demo_seed_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            env = os.environ.copy()
            env["DATABASE_URL"] = "sqlite:///" + str(Path(directory) / "demo.db").replace("\\", "/")
            command = [sys.executable, "scripts/demo-seed/reset_demo.py"]
            first = subprocess.run(command, cwd=ROOT, env=env, check=True, capture_output=True, text=True)
            second = subprocess.run(command, cwd=ROOT, env=env, check=True, capture_output=True, text=True)
            self.assertEqual(json.loads(first.stdout)["cards"], 5)
            self.assertEqual(json.loads(second.stdout)["cards"], 5)
            self.assertEqual(json.loads(second.stdout)["ratings"], 1)

    def test_plan_b_rehearsal(self):
        completed = subprocess.run(
            [sys.executable, "scripts/demo-rehearsal.py"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0)
        report = json.loads((ROOT / "artifacts" / "demo" / "plan-b-rehearsal.json").read_text(encoding="utf-8"))
        self.assertTrue(report["degradation"]["fallback_used"])
        self.assertTrue(report["video_backup"]["readable"])


if __name__ == "__main__":
    unittest.main()
