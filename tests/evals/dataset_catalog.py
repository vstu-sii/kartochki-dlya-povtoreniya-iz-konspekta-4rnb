"""One explicit, fail-closed catalog shared by all Quality runners."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATASET_VERSION = "lab4-v3"
DATASETS = tuple(ROOT / "docs/quality/golden-dataset" / name for name in (
    "dataset.jsonl", "dataset-v2-additions.jsonl", "dataset-v3-additions.jsonl",
))
OPERATIONS = {"generate_card", "review_answer", "reject_input", "validate_model_output",
              "rate_card", "resume_session", "complete_session", "budget_limit", "tool_timeout"}


def load_dataset(paths=DATASETS):
    records, seen = [], set()
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            case = json.loads(line)
            if case["id"] in seen:
                raise ValueError(f"Duplicate dataset ID: {case['id']}")
            if case["operation"] not in OPERATIONS:
                raise ValueError(f"Unsupported operation: {case['operation']}")
            seen.add(case["id"])
            records.append(case)
    if not records:
        raise ValueError("Empty dataset")
    return records


def dataset_hash():
    return hashlib.sha256(b"".join(path.read_bytes() for path in DATASETS)).hexdigest()
