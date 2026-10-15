"""Offline A/B comparison of the lab3 reviewer and prompt-v2 reviewer."""

import argparse
import json
import time
from pathlib import Path

from ml.models.baseline import BaselineModel


def old_review(model: BaselineModel, reference: str, answer: str) -> str:
    reference_words = {word for word in model._normalize(reference).split() if len(word) > 2}
    answer_words = {word for word in model._normalize(answer).split() if len(word) > 2}
    coverage = len(reference_words & answer_words) / max(1, len(reference_words))
    if coverage >= 0.72:
        return "correct"
    if coverage >= 0.18:
        return "partially_correct"
    return "incorrect"


def run(dataset_path: Path) -> dict:
    cases = [json.loads(line) for line in dataset_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    review_cases = [case for case in cases if case.get("operation") == "review_answer"]
    model = BaselineModel()
    started = time.perf_counter()
    a_ok = b_ok = 0
    examples = []
    tokens_a = tokens_b = 0
    for case in review_cases:
        fields = case["input"]
        expected = case["expected_output"]["verdict"]
        a_verdict = old_review(model, fields["reference_answer"], fields["student_answer"])
        b_result = model._deterministic_review(
            {
                "question": fields["question"],
                "reference_answer": fields["reference_answer"],
                "source_quote": case.get("context", [{}])[0].get("text", ""),
            },
            fields["student_answer"],
        )
        b_verdict = b_result["verdict"]
        a_ok += a_verdict == expected
        b_ok += b_verdict == expected
        old_prompt = (
            "Оцени ответ по совпадению с эталоном. "
            + fields["reference_answer"]
            + " Ответ: "
            + fields["student_answer"]
        )
        new_prompt = model._review_prompt(
            {
                "question": fields["question"],
                "reference_answer": fields["reference_answer"],
                "source_quote": case.get("context", [{}])[0].get("text", ""),
            },
            fields["student_answer"],
        )
        tokens_a += max(1, len(old_prompt) // 4)
        tokens_b += max(1, len(new_prompt) // 4)
        if a_verdict != b_verdict and len(examples) < 8:
            examples.append({"id": case["id"], "expected": expected, "a": a_verdict, "b": b_verdict})
    count = len(review_cases)
    return {
        "experiment": "lab4-review-prompts-ab",
        "dataset": str(dataset_path).replace("\\", "/"),
        "case_count": count,
        "variant_a": {"name": "lab3-lexical-v1", "agreement": round(a_ok / count, 4), "estimated_input_tokens": tokens_a},
        "variant_b": {"name": "review-v2.1", "agreement": round(b_ok / count, 4), "estimated_input_tokens": tokens_b},
        "delta_agreement_pp": round((b_ok - a_ok) * 100 / count, 2),
        "changed_examples": examples,
        "duration_ms": round((time.perf_counter() - started) * 1000),
        "decision": "B" if b_ok >= a_ok else "A",
        "notes": "Offline deterministic comparison; provider latency and billing are intentionally not inferred.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path("docs/quality/golden-dataset/dataset.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/experiments/lab4-ab-results.json"))
    args = parser.parse_args()
    result = run(args.dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
