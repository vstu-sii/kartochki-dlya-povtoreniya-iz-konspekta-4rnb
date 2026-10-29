import unittest

from tests.evals.run_lab6_demo import (
    CONCEPT_SOURCE,
    validate_generation,
    validate_review,
)


class Lab6DemoRunnerTest(unittest.TestCase):
    def test_generation_requires_exact_grounded_gemini_result(self):
        cards = [
            {
                "question": f"Вопрос {index}?",
                "reference_answer": "Ответ",
                "source_page": 1,
                "source_quote": "Кэш процессора ускоряет доступ к часто используемым данным.",
                "difficulty": "basic",
            }
            for index in range(5)
        ]
        valid, errors = validate_generation(
            {
                "cards": cards,
                "model": "gemini-test",
                "fallback_used": False,
                "trace_id": "trace",
            },
            CONCEPT_SOURCE,
        )
        self.assertTrue(valid, errors)

        cards[0]["source_quote"] = "Выдуманная цитата"
        valid, errors = validate_generation(
            {
                "cards": cards,
                "model": "gemini-test",
                "fallback_used": False,
                "trace_id": "trace",
            },
            CONCEPT_SOURCE,
        )
        self.assertFalse(valid)
        self.assertIn("not grounded", " ".join(errors))

    def test_review_correction_may_be_in_feedback_or_missing_points(self):
        response = {
            "verdict": "incorrect",
            "feedback": "Ответ содержит ошибку.",
            "missing_points": ["Процессор обращается к оперативной памяти"],
            "model": "gemini-test",
            "fallback_used": False,
            "trace_id": "trace",
            "review_id": "review",
        }
        valid, errors = validate_review(
            response,
            {"incorrect", "partially_correct"},
            ("оператив",),
        )
        self.assertTrue(valid, errors)

    def test_review_rejects_fallback_and_wrong_verdict(self):
        valid, errors = validate_review(
            {
                "verdict": "correct",
                "feedback": "Верно",
                "missing_points": [],
                "model": "deterministic-review-v5",
                "fallback_used": True,
                "trace_id": "trace",
                "review_id": "review",
            },
            {"incorrect"},
        )
        self.assertFalse(valid)
        self.assertGreaterEqual(len(errors), 3)


if __name__ == "__main__":
    unittest.main()
