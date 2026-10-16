"""Versioned prompt templates."""

from pathlib import Path


def load_prompt(name: str) -> str:
    return (Path(__file__).parent / f"{name}.txt").read_text(encoding="utf-8")
