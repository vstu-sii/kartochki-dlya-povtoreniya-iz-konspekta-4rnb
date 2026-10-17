"""Versioned prompt templates and their single version manifest."""

import json
from pathlib import Path


_ROOT = Path(__file__).parent


def load_prompt(name: str) -> str:
    return (_ROOT / f"{name}.txt").read_text(encoding="utf-8")


def prompt_versions() -> dict[str, str]:
    return json.loads((_ROOT / "versions.json").read_text(encoding="utf-8"))
