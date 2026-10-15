import tempfile
import unittest
from pathlib import Path

from ml.models.baseline import BaselineModel
from ml.tracing.client import TraceClient


class BaselineTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.trace_path = Path(self.temp.name) / "traces.jsonl"
        self.model = BaselineModel(TraceClient(str(self.trace_path)))

    def tearDown(self):
        self.temp.cleanup()

    def test_generation_is_structured_grounded_and_traced(self):
        text = "Кэш ускоряет доступ к часто используемым данным."
        result = self.model.generate({"pages": [{"page": 1, "text": text}], "requested_card_count": 5})
        self.assertEqual(1, len(result["cards"]))
        self.assertTrue(all(card["source_quote"] in text for card in result["cards"]))
        self.assertTrue(self.trace_path.exists())

    def test_review_returns_contract_fields(self):
        result = self.model.review(
            {
                "card": {"question": "Что делает кэш?", "reference_answer": "Кэш ускоряет доступ к данным."},
                "student_answer": "Он ускоряет доступ к данным.",
            }
        )
        self.assertEqual("correct", result["verdict"])
        self.assertIn("trace_id", result)

    def test_pdf_heading_is_not_used_as_question_topic(self):
        text = (
            "1 Лабораторная работа №3\n"
            "Цель: освоить установку и настройку PostgreSQL.\n"
            "Реляционная база данных хранит сведения в связанных таблицах."
        )
        result = self.model.generate({"pages": [{"page": 1, "text": text}], "requested_card_count": 5})
        first = result["cards"][0]
        self.assertEqual("Какова цель этой работы?", first["question"])
        self.assertNotIn("Лабораторная работа", first["question"])
        self.assertIn(first["source_quote"], text)


if __name__ == "__main__":
    unittest.main()
