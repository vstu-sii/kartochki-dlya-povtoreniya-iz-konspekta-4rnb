"""Honest Lab4 experiments: algorithm A/B, prompt contract, and provider prompt A/B."""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from ml.models.baseline import BaselineModel, PRIMARY_MODEL


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT / "docs/quality/golden-dataset/dataset.jsonl"
PROMPT_DIR = ROOT / "ml/prompts_v2"


def load_cases(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def render(template_name: str, case: dict) -> str:
    template = (PROMPT_DIR / f"{template_name}.txt").read_text(encoding="utf-8")
    fields = case["input"]
    context = "\n".join(f"[page {p['page']}] {p['text']}" for p in case.get("context", []))
    return template.format(
        requested_card_count=fields.get("requested_card_count", 5),
        language=fields.get("language", "ru"),
        context=context,
        question=fields.get("question", ""),
        reference_answer=fields.get("reference_answer", ""),
        source_quote=context,
        student_answer=fields.get("student_answer", ""),
    )


def old_review(model: BaselineModel, reference: str, answer: str) -> str:
    reference_words = {word for word in model._normalize(reference).split() if len(word) > 2}
    answer_words = {word for word in model._normalize(answer).split() if len(word) > 2}
    coverage = len(reference_words & answer_words) / max(1, len(reference_words))
    if coverage >= 0.72:
        return "correct"
    if coverage >= 0.18:
        return "partially_correct"
    return "incorrect"


def run_algorithm_ab(cases: list[dict]) -> dict:
    """Preserve the historical comparison under its accurate name."""
    review_cases = [case for case in cases if case.get("operation") == "review_answer"]
    model = BaselineModel()
    rows = []
    for case in review_cases:
        fields = case["input"]
        expected = case["expected_output"]["verdict"]
        a = old_review(model, fields["reference_answer"], fields["student_answer"])
        b = model._deterministic_review(
            {
                "question": fields["question"],
                "reference_answer": fields["reference_answer"],
                "source_quote": case.get("context", [{}])[0].get("text", ""),
            },
            fields["student_answer"],
        )["verdict"]
        rows.append({"id": case["id"], "expected": expected, "a": a, "b": b,
                     "a_correct": a == expected, "b_correct": b == expected})
    count = len(rows)
    a_score = sum(row["a_correct"] for row in rows) / count
    b_score = sum(row["b_correct"] for row in rows) / count
    return {
        "experiment": "review-algorithm-ab",
        "claim_scope": "Local deterministic reviewer algorithms; not prompt or LLM quality.",
        "case_count": count,
        "variant_a": {"name": "lexical-overlap-v1", "agreement": round(a_score, 4)},
        "variant_b": {"name": "normalized-semantic-rules-v2", "agreement": round(b_score, 4)},
        "delta_agreement_pp": round((b_score - a_score) * 100, 2),
        "cases": rows,
        "decision": "B" if b_score >= a_score else "A",
    }


def run_contract(cases: list[dict]) -> dict:
    """Provider-free rendering/schema check; deliberately no quality claim."""
    selected = [case for case in cases if case.get("operation") in {"generate_card", "review_answer"}]
    rows = []
    for case in selected:
        prefix = "generation" if case["operation"] == "generate_card" else "review"
        prompts = {variant: render(f"{prefix}-{variant}", case) if variant == "v1" else render(prefix, case)
                   for variant in ("v1", "v2")}
        row = {
            "id": case["id"], "operation": case["operation"],
            "rendered": all(bool(value.strip()) for value in prompts.values()),
            "estimated_input_tokens": {key: max(1, len(value) // 4) for key, value in prompts.items()},
            "only_changed_factor": "prompt_text",
        }
        rows.append(row)
    passed = all(row["rendered"] for row in rows)
    return {
        "experiment": "prompt-ab-contract-check",
        "provider_called": False,
        "quality_measured": False,
        "case_count": len(rows),
        "passed": passed,
        "note": "Both variants render on the same cases; this is not an LLM A/B result.",
        "cases": rows,
    }


def _grade_generation(case: dict, response: dict) -> bool:
    expected = case["expected_output"]
    cards = response.get("cards", [])
    forbidden = " ".join(expected.get("forbidden_facts", [])).lower()
    for card in cards:
        serialized = json.dumps(card, ensure_ascii=False).lower()
        if (card.get("source_page") == expected.get("source_page")
                and expected.get("required_quote", "") in card.get("source_quote", "")
                and (not forbidden or forbidden not in serialized)):
            return True
    return False


def run_provider_prompt_ab(cases: list[dict], model_name: str, repeats: int) -> dict:
    """Run a real prompt-only A/B with identical model, schema and parameters."""
    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY is required for --mode provider")
    model = BaselineModel()
    selected = [case for case in cases if case.get("operation") in {"generate_card", "review_answer"}]
    rows = []
    totals = {"a": {"correct": 0, "tokens": 0}, "b": {"correct": 0, "tokens": 0}}
    for repeat in range(repeats):
        for case in selected:
            operation = case["operation"]
            prefix = "generation" if operation == "generate_card" else "review"
            schema = model._cards_schema(case["input"].get("requested_card_count", 5)) if operation == "generate_card" else model._review_schema()
            for variant, template in (("a", f"{prefix}-v1"), ("b", prefix)):
                prompt = render(template, case)
                started = time.perf_counter()
                response = model._call_gemini(prompt, schema, model_name)
                usage = response.pop("_usage", {})
                if operation == "review_answer":
                    correct = response.get("verdict") == case["expected_output"]["verdict"]
                else:
                    correct = _grade_generation(case, response)
                tokens = int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0))
                totals[variant]["correct"] += int(correct)
                totals[variant]["tokens"] += tokens
                rows.append({"id": case["id"], "repeat": repeat + 1, "operation": operation,
                             "variant": variant.upper(), "correct": correct, "usage": usage,
                             "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                             "response": response})
    denominator = len(selected) * repeats
    return {
        "experiment": "provider-prompt-only-ab",
        "provider_called": True,
        "model": model_name,
        "parameters": {"response_mime_type": "application/json", "thinking_level": "low",
                       "max_output_tokens": 6000, "temperature": "not sent", "repeats": repeats},
        "controlled_variables": ["dataset", "model", "generation parameters", "schema", "grader"],
        "changed_factor": "prompt_text_only",
        "variant_a": {"prompt": "v1", "agreement": round(totals["a"]["correct"] / denominator, 4),
                      "tokens": totals["a"]["tokens"]},
        "variant_b": {"prompt": "v2", "agreement": round(totals["b"]["correct"] / denominator, 4),
                      "tokens": totals["b"]["tokens"]},
        "cases": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--mode", choices=("algorithm", "contract", "provider"), default="algorithm")
    parser.add_argument("--model", default=PRIMARY_MODEL)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--min-b-agreement", type=float, default=0.85)
    parser.add_argument("--fail-on-regression", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cases = load_cases(args.dataset)
    if args.mode == "algorithm":
        result = run_algorithm_ab(cases)
        failed = result["variant_b"]["agreement"] < args.min_b_agreement
        if args.fail_on_regression:
            failed = failed or result["variant_b"]["agreement"] < result["variant_a"]["agreement"]
    elif args.mode == "contract":
        result = run_contract(cases)
        failed = not result["passed"]
    else:
        result = run_provider_prompt_ab(cases, args.model, max(1, args.repeats))
        failed = result["variant_b"]["agreement"] < args.min_b_agreement
        if args.fail_on_regression:
            failed = failed or result["variant_b"]["agreement"] < result["variant_a"]["agreement"]
    result.update({"run_at": datetime.now(timezone.utc).isoformat(),
                   "dataset": str(args.dataset).replace("\\", "/"), "mode": args.mode})
    output = args.output or ROOT / f"artifacts/experiments/lab4-{args.mode}-results.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result.get(key) for key in ("experiment", "variant_a", "variant_b", "passed")}, ensure_ascii=False))
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
