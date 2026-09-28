"""Acceptance checks for the Lab 2 AI Engineer deliverables."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Lab2AIArtifactsTest(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        path = ROOT / relative_path
        self.assertTrue(path.is_file(), f"Missing artifact: {relative_path}")
        return path.read_text(encoding="utf-8")

    def test_ai_pipeline_contains_required_design_parts(self) -> None:
        text = self.read("docs/ai-pipeline.md")
        required_markers = (
            "```plantuml",
            "Контроль качества",
            "Логирование и наблюдаемость",
            "Границы контекста",
            "Prompt builder",
            "Model gateway",
        )
        for marker in required_markers:
            self.assertIn(marker, text)

    def test_model_decision_contains_fallback_and_cost(self) -> None:
        text = self.read("docs/model-candidates.md")
        for marker in (
            "Решение лаборатории 2",
            "gemini-3.8-flash",
            "gemini-3.5-flash-lite",
            "План деградации",
            "Цена решения",
            "$0.02625",
        ):
            self.assertIn(marker, text)

    def test_spike_note_names_assumptions_and_honest_results(self) -> None:
        text = self.read("docs/experiments/lab2.md")
        for marker in (
            "Непроверенные допущения",
            "Спайк 1",
            "Спайк 2",
            "сработало",
            "сработало иначе",
            "Не доказано",
        ):
            self.assertIn(marker, text)

    def test_notebook_is_valid_and_reproducible(self) -> None:
        notebook = json.loads(self.read("notebooks/lab2_spikes.ipynb"))
        self.assertEqual(notebook["nbformat"], 4)
        code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
        self.assertGreaterEqual(len(code_cells), 5)
        self.assertTrue(all(isinstance(cell["execution_count"], int) for cell in code_cells))

        namespace: dict[str, object] = {}
        for cell in code_cells:
            exec("".join(cell["source"]), namespace)
        self.assertEqual(namespace["results"]["valid"], [])
        self.assertTrue(namespace["results"]["missing_quote"])
        self.assertTrue(namespace["results"]["hallucinated_quote"])

    def test_openapi_contains_endpoints_and_structured_outputs(self) -> None:
        text = self.read("api/openapi.yaml")
        required_markers = (
            "openapi: 3.1.0",
            "/v1/ai/card-sets:",
            "/v1/ai/answer-reviews:",
            "CardSet:",
            "AnswerReview:",
            "source_quote:",
            "fallback_used:",
            "MODEL_OUTPUT_INVALID",
        )
        for marker in required_markers:
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
