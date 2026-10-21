import copy
import unittest

from tests.evals.prepare_lab1_quality_evidence import build_report, summarize_existing


class Lab1QualityEvidenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report(20)

    def test_contains_exactly_twenty_raw_answer_reviews(self):
        section = self.report["answer_review_check"]
        self.assertEqual(section["case_count"], 20)
        self.assertEqual(len(section["rows"]), 20)
        self.assertEqual(len({row["case_id"] for row in section["rows"]}), 20)

    def test_human_only_measurements_are_not_fabricated(self):
        self.assertIsNone(self.report["pdf_thesis_check"]["accuracy"])
        self.assertIsNone(self.report["formula_extraction_check"]["loss_rate"])
        self.assertIsNone(self.report["scenario_cost_check"]["full_scenario"]["calculated_cost_usd"])
        for row in self.report["answer_review_check"]["rows"]:
            self.assertTrue(all(value is None for value in row["quality_manual_review"].values()))

    def test_complete_raw_inputs_are_summarized(self):
        report = copy.deepcopy(self.report)
        for row in report["answer_review_check"]["rows"]:
            row["quality_manual_review"].update(
                no_contradiction=True,
                mandatory_points_complete=True,
                critical_tone_violation=False,
                minor_tone_violation=False,
            )
        report["pdf_thesis_check"]["documents"] = [
            {"file": "example.pdf", "theses": [{"text": "T1", "correct": True}, {"text": "T2", "correct": False}]}
        ]
        report["formula_extraction_check"]["documents"] = [
            {"file": "example.pdf", "source_formula_count": 10, "extracted_formula_count": 9}
        ]
        report["scenario_cost_check"]["full_scenario"].update(
            model="provider-model",
            input_tokens=20_000,
            output_tokens=3_000,
            input_price_usd_per_million=0.75,
            output_price_usd_per_million=3.75,
        )
        report["live_latency_check"].update(
            version_or_git_sha="abc123",
            environment="staging",
            model="provider-model",
            pdf_to_cards_runs_ms=[10_000, 20_000],
            answer_to_review_runs_ms=[5_000, 6_000],
        )
        summarized = summarize_existing(report)
        self.assertEqual(summarized["answer_review_check"]["metrics"]["no_contradiction_rate"], 1.0)
        self.assertEqual(summarized["pdf_thesis_check"]["accuracy"], 0.5)
        self.assertEqual(summarized["formula_extraction_check"]["loss_rate"], 0.1)
        self.assertEqual(summarized["scenario_cost_check"]["full_scenario"]["calculated_cost_usd"], 0.02625)
        self.assertEqual(summarized["live_latency_check"]["answer_to_review_p95_ms"], 6000)


if __name__ == "__main__":
    unittest.main()
