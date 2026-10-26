import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

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
        event = json.loads(self.trace_path.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual("[redacted]", event["prompt_preview"])
        self.assertNotIn(text, json.dumps(event, ensure_ascii=False))

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

    def test_gemini_review_accepts_a_semantically_equivalent_answer(self):
        semantic_result = {
            "verdict": "correct",
            "score": 2,
            "feedback": "Смысл передан верно своими словами.",
            "missing_points": [],
            "_usage": {"input_tokens": 50, "output_tokens": 20},
        }
        with patch.dict("os.environ", {"MODEL_PROVIDER": "gemini", "GEMINI_API_KEY": "test"}):
            model = BaselineModel(TraceClient(str(self.trace_path)))
            with patch.object(model, "_call_gemini", return_value=semantic_result):
                result = model.review(
                    {
                        "card": {
                            "question": "Зачем нужен кэш?",
                            "reference_answer": "Кэш сокращает время доступа к часто используемым данным.",
                            "source_quote": "Кэш сокращает время доступа к часто используемым данным.",
                        },
                        "student_answer": "Чтобы быстрее получать сведения, которые нужны чаще всего.",
                    }
                )
        self.assertEqual("correct", result["verdict"])
        self.assertEqual("gemini-3.8-flash", result["model"])
        self.assertFalse(result["fallback_used"])

    def test_invalid_gemini_review_falls_back_safely(self):
        with patch.dict("os.environ", {"MODEL_PROVIDER": "gemini", "GEMINI_API_KEY": "test"}):
            model = BaselineModel(TraceClient(str(self.trace_path)))
            with patch.object(model, "_call_gemini", return_value={"verdict": "correct", "score": 0}):
                result = model.review(
                    {
                        "card": {"question": "Что делает кэш?", "reference_answer": "Кэш ускоряет доступ к данным."},
                        "student_answer": "Он ускоряет доступ к данным.",
                    }
                )
        self.assertTrue(result["fallback_used"])
        self.assertEqual("gemini_invalid_output", result["fallback_reason"])
        self.assertEqual("deterministic-review-v4", result["model"])

    def test_semantic_equivalents_do_not_create_false_missing_points(self):
        cases = (
            (
                "Процессор обращается к оперативной памяти.",
                "Процессор идёт за данными в RAM.",
                "correct",
                [],
            ),
            (
                "Потоки разделяют память процесса; процессы имеют отдельные адресные пространства.",
                "Потоки одного процесса используют общую память.",
                "partially_correct",
                ["Процессы имеют отдельные адресные пространства."],
            ),
            (
                "Вход только одного потока в критическую секцию.",
                "Только одному потоку.",
                "partially_correct",
                ["Вход в критическую секцию."],
            ),
        )
        for reference, answer, verdict, missing in cases:
            with self.subTest(answer=answer):
                result = self.model.review(
                    {"card": {"question": "Q", "reference_answer": reference}, "student_answer": answer}
                )
                self.assertEqual(verdict, result["verdict"])
                self.assertEqual(missing, result["missing_points"])

    def test_complete_mandatory_meaning_is_not_downgraded(self):
        result = self.model.review(
            {
                "card": {"question": "Что добавляет HTTPS?", "reference_answer": "TLS-защиту данных между клиентом и сервером."},
                "student_answer": "Использует TLS для защиты данных.",
            }
        )
        self.assertEqual("correct", result["verdict"])
        self.assertEqual([], result["missing_points"])

    def test_explicit_acronym_requirement_is_explained(self):
        result = self.model.review(
            {
                "card": {"question": "Как работает очередь?", "reference_answer": "По принципу FIFO."},
                "student_answer": "Первым добавлен — первым извлечён.",
            }
        )
        self.assertEqual("partially_correct", result["verdict"])
        self.assertEqual(["Не назван термин FIFO."], result["missing_points"])

    def test_semantic_aliases_do_not_accept_contradictions(self):
        cases = (
            ("Данные загружаются в оперативную память.", "RAM — это жёсткий диск."),
            ("Потоки разделяют память процесса.", "Потоки не разделяют память процесса."),
            ("В критическую секцию входит только один поток.", "Одновременно входят несколько потоков."),
            ("Очередь работает по принципу FIFO.", "Очередь работает по принципу LIFO."),
        )
        for reference, answer in cases:
            with self.subTest(answer=answer):
                result = self.model.review(
                    {"card": {"question": "Q", "reference_answer": reference}, "student_answer": answer}
                )
                self.assertEqual("incorrect", result["verdict"])

    def test_mixed_cache_answer_corrects_disk_without_confirming_it(self):
        answer = "Данных нет в кэше, поэтому процессор обращается к жёсткому диску."
        result = self.model.review(
            {
                "card": {
                    "question": "Что происходит при промахе кэша?",
                    "reference_answer": "Процессор не находит данные в кэше и обращается к оперативной памяти.",
                },
                "student_answer": answer,
            }
        )
        self.assertNotEqual("correct", result["verdict"])
        self.assertIn("Верно: Процессор не находит данные в кэше.", result["feedback"])
        self.assertIn("оперативной памяти, а не к жёсткому диску", result["feedback"])
        self.assertNotIn(f"Верно: {answer}", result["feedback"])

    def test_other_mixed_answer_does_not_repeat_whole_error_as_correct(self):
        answer = "Потоки разделяют память процесса, и процессы тоже используют общую память."
        result = self.model.review(
            {
                "card": {
                    "question": "Чем потоки отличаются от процессов?",
                    "reference_answer": "Потоки разделяют память процесса; процессы имеют отдельные адресные пространства.",
                },
                "student_answer": answer,
            }
        )
        self.assertEqual("partially_correct", result["verdict"])
        self.assertIn("процессы имеют отдельные адресные пространства, а не общую память", result["feedback"])
        self.assertNotIn(f"Верно: {answer}", result["feedback"])


if __name__ == "__main__":
    unittest.main()
