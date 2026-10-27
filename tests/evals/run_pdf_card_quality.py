"""Generate reproducible PDF-card evidence without inventing human labels."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.pdf_extractor import extract_pdf_pages  # noqa: E402
from ml.models.baseline import BaselineModel  # noqa: E402


class SilentTrace:
    def record(self, *args, **kwargs) -> None:
        return None


def git_metadata() -> dict:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    return {"git_sha": commit, "working_tree_clean": not bool(status)}


def read_source(pdf: str | None, git_object: str | None) -> tuple[bytes, dict]:
    if pdf:
        path = Path(pdf).resolve()
        return path.read_bytes(), {"kind": "file", "value": str(path)}
    raw = subprocess.check_output(["git", "show", git_object], cwd=ROOT)
    return raw, {"kind": "git_object", "value": git_object}


def quote_is_grounded(quote: str, page_text: str) -> bool:
    flexible = re.compile(r"\s+".join(re.escape(part) for part in quote.split()))
    return bool(flexible.search(page_text))


def looks_complete(text: str) -> bool:
    normalized = " ".join(text.split()).strip()
    if not normalized or normalized.endswith(","):
        return False
    last_word = re.sub(r"[^A-Za-zА-Яа-яЁё/-]", "", normalized.split()[-1]).lower()
    if last_word in {"к", "в", "во", "на", "с", "со", "для", "из", "по", "и", "или", "но", "а"}:
        return False
    return normalized.endswith((".", "!", "?", ";", ")", "»"))


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--pdf")
    source.add_argument("--git-object")
    parser.add_argument("--output", required=True)
    parser.add_argument("--count", type=int, default=5)
    args = parser.parse_args()

    raw, source_ref = read_source(args.pdf, args.git_object)
    extracted = extract_pdf_pages(raw)
    pages = [{"page": page.page, "text": page.text} for page in extracted]
    result = BaselineModel(SilentTrace()).generate(
        {"pages": pages, "requested_card_count": max(1, args.count)}
    )
    page_text = {page["page"]: page["text"] for page in pages}
    rows = []
    for card in result["cards"]:
        rows.append(
            {
                "card": card,
                "automatic_checks": {
                    "quote_grounded": quote_is_grounded(
                        card["source_quote"], page_text.get(card["source_page"], "")
                    ),
                    "statement_looks_complete": looks_complete(card["reference_answer"]),
                },
                "quality_manual_review": {
                    "thesis_correct": None,
                    "standalone_complete_statement": None,
                    "reviewer": None,
                    "comment": None,
                },
            }
        )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "tests/evals/run_pdf_card_quality.py",
        "generation_command": " ".join(sys.argv),
        "source_revision": git_metadata(),
        "source": source_ref,
        "source_pdf_sha256": hashlib.sha256(raw).hexdigest(),
        "page_count": len(pages),
        "model": result["model"],
        "prompt_version": result["prompt_version"],
        "card_count": len(rows),
        "automatic_summary": {
            "grounded_count": sum(row["automatic_checks"]["quote_grounded"] for row in rows),
            "looks_complete_count": sum(
                row["automatic_checks"]["statement_looks_complete"] for row in rows
            ),
        },
        "human_thesis_accuracy": None,
        "note": "Automatic completeness is a guard, not the Lab1 human accuracy metric.",
        "rows": rows,
    }
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), **report["automatic_summary"]}, ensure_ascii=False))
    return 0 if all(row["automatic_checks"].values() for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
