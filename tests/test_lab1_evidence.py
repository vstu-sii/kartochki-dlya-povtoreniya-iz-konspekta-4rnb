"""Reject evidence tampering and keep pending review distinct from acceptance."""
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent / "evals"))
from audit_lab1_evidence import ROOT, validate_snapshot
from dataset_catalog import dataset_hash


class Lab1EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = json.loads((ROOT / "artifacts/evals/lab1-ai-quality-evidence.json").read_text(encoding="utf-8-sig"))

        # This in-memory fixture tests current validation, not historical provenance.
        # The reviewed first 20 rows are unchanged; keep the frozen file untouched.
        cls.snapshot["dataset_sha256"] = dataset_hash()

    def test_automatic_agreement_does_not_complete_human_review(self):
        pending = copy.deepcopy(self.snapshot)
        for row in pending["answer_review_check"]["rows"]:
            for key in row["quality_manual_review"]:
                row["quality_manual_review"][key] = None
        for key in pending["answer_review_check"]["metrics"]:
            pending["answer_review_check"]["metrics"][key] = None
        _, agreement, reviewed = validate_snapshot(pending)
        self.assertEqual(agreement["matched"], 20)
        self.assertEqual(reviewed, 0)

    def test_stale_manual_totals_are_rejected(self):
        altered = copy.deepcopy(self.snapshot)
        altered["answer_review_check"]["metrics"]["no_contradiction_rate"] = -1
        with self.assertRaises(ValueError):
            validate_snapshot(altered)

    def test_changed_source_and_duplicate_ids_are_rejected(self):
        for field in ("question", "source_context", "mandatory_points", "expected_verdict"):
            with self.subTest(field=field):
                altered = copy.deepcopy(self.snapshot)
                altered["answer_review_check"]["rows"][0][field] = "tampered"
                with self.assertRaises(ValueError):
                    validate_snapshot(altered)
        altered = copy.deepcopy(self.snapshot)
        altered["answer_review_check"]["rows"][1] = altered["answer_review_check"]["rows"][0]
        with self.assertRaises(ValueError):
            validate_snapshot(altered)

    def test_wrong_dataset_and_inflated_agreement_are_rejected(self):
        altered = copy.deepcopy(self.snapshot)
        altered["dataset_sha256"] = "wrong"
        with self.assertRaises(ValueError):
            validate_snapshot(altered)
        altered = copy.deepcopy(self.snapshot)
        altered["answer_review_check"]["rows"][0]["system_result"]["verdict"] = "incorrect"
        with self.assertRaises(ValueError):
            validate_snapshot(altered)

    def test_string_boolean_is_rejected(self):
        altered = copy.deepcopy(self.snapshot)
        altered["answer_review_check"]["rows"][0]["quality_manual_review"]["no_contradiction"] = "true"
        with self.assertRaises(ValueError):
            validate_snapshot(altered)


if __name__ == "__main__":
    unittest.main()
