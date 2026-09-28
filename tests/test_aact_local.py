"""Local architecture boundary check equivalent to aact rules used in Lab 2."""

from __future__ import annotations

import re
import unittest
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTAINER = ROOT / "docs/architecture/c4-container.puml"
CONFIG = ROOT / "aact.config.ts"

FORBIDDEN = {
    ("app_api", "gemini"),
    ("app_api", "postgres"),
    ("ai_service", "postgres"),
    ("telegram_adapter", "postgres"),
    ("telegram_adapter", "gemini"),
    ("data_service", "gemini"),
    ("app_api", "telegram"),
}


def relations(text: str) -> list[tuple[str, str]]:
    return re.findall(r"Rel\((\w+),\s*(\w+)", text)


def has_cycle(edges: list[tuple[str, str]]) -> bool:
    graph: dict[str, list[str]] = defaultdict(list)
    for src, dst in edges:
        graph[src].append(dst)
    visited: set[str] = set()
    stack: set[str] = set()

    def dfs(node: str) -> bool:
        if node in stack:
            return True
        if node in visited:
            return False
        visited.add(node)
        stack.add(node)
        for nxt in graph[node]:
            if dfs(nxt):
                return True
        stack.remove(node)
        return False

    return any(dfs(node) for node in list(graph))


class AactLocalCheckTest(unittest.TestCase):
    def test_aact_rules_have_zero_violations(self) -> None:
        text = CONTAINER.read_text(encoding="utf-8")
        config = CONFIG.read_text(encoding="utf-8")
        edges = relations(text)
        violations: list[str] = []

        for edge in edges:
            if edge in FORBIDDEN:
                violations.append(f"forbidden relation {edge}")

        db_owners = [src for src, dst in edges if dst == "postgres"]
        if db_owners != ["data_service"]:
            violations.append(f"dbPerService failed: owners={db_owners}")

        if text.count('$tags="acl"') < 2:
            violations.append("acl adapters not tagged")
        if text.count('$tags="repo"') < 1:
            violations.append("data owner not tagged")

        if has_cycle(edges):
            violations.append("acyclic failed: cycle detected")

        for rule in ("acyclic: true", "acl: true", "dbPerService: true", "commonReuse: true"):
            self.assertIn(rule, config)

        self.assertEqual(violations, [], f"aact local violations: {violations}")


if __name__ == "__main__":
    unittest.main()
