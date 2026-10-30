"""Negative controls: corrupt/missing evidence must never produce a green gate."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "evals"))
from dataset_catalog import load_dataset
from run_evals import failed_thresholds, load_cases, MINI_IDS, run
from run_full_suite import coverage


class GateContractTest(unittest.TestCase):
    def test_bad_and_unmeasured_metrics_fail(self):
        for value in (0.5, None):
            self.assertEqual(["safety_guard_rate"], failed_thresholds(
                {"metrics": {"safety_guard_rate": value}}, {"safety_guard_rate": 1}))

    def test_missing_case_cannot_be_counted_as_covered(self):
        actual = coverage({"cases": [{"id": "a", "executed": False}]}, {"cases": []}, {"a"})
        self.assertEqual(["a"], actual["missing_ids"])

    def test_duplicate_and_unknown_operations_are_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.jsonl"
            row = {"id": "x", "operation": "generate_card"}
            path.write_text((json.dumps(row) + "\n") * 2, encoding="utf-8")
            with self.assertRaises(ValueError):
                load_dataset((path,))
            path.write_text(json.dumps({**row, "operation": "unimplemented"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_dataset((path,))

    def test_retry_subset_cannot_silently_claim_full_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            report=run(False,Path(directory)/"retry.json",case_ids={"SAFE-001"})
        self.assertEqual(report["selected_case_ids"],["SAFE-001"])
        self.assertEqual(report["dataset_case_count"],1)
        self.assertEqual(len(report["cases"]),1)

    def test_unknown_retry_id_is_rejected_before_model_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                run(False,Path(directory)/"retry.json",case_ids={"MISSING-CASE"})

    def test_mini_is_fixed_and_lab4_additions_are_loaded(self):
        self.assertEqual(MINI_IDS, {row["id"] for row in load_cases(True)})
        self.assertTrue({"SEC-L4-001", "SEC-L4-002", "BUDGET-L4-001", "TOOL-L4-001"}
                        .issubset({row["id"] for row in load_dataset()}))
