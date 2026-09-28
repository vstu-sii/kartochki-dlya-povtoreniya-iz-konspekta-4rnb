"""Dependency-free checks for the complete Lab 2 artifact set."""

from __future__ import annotations

import json
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Lab2AllArtifactsTest(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        path = ROOT / relative_path
        self.assertTrue(path.is_file(), f"Missing: {relative_path}")
        return path.read_text(encoding="utf-8")

    def test_product_artifacts(self) -> None:
        use_cases = self.read("docs/use-cases/README.md")
        for uc in range(1, 6):
            self.assertIn(f"UC-0{uc}", use_cases)
        for marker in ("Актёр", "Цель", "Контекст", "Основной сценарий", "Результат"):
            self.assertGreaterEqual(use_cases.count(marker), 5)

        roadmap = self.read("docs/roadmap.md")
        self.assertIn("Явный не-скоуп", roadmap)
        self.assertIn("Demo Day", roadmap)

        glossary = self.read("docs/glossary.md")
        term_rows = [line for line in glossary.splitlines() if line.startswith("|")]
        self.assertGreaterEqual(len(term_rows) - 2, 30)

    def test_diagrams_and_architecture_boundaries(self) -> None:
        for name in ("c4-context.puml", "c4-container.puml", "erd.puml"):
            text = self.read(f"docs/architecture/{name}")
            self.assertIn("@startuml", text)
            self.assertIn("@enduml", text)

        container = self.read("docs/architecture/c4-container.puml")
        for expected in ("$tags=\"acl\"", "$tags=\"repo\"", "Rel(data_service, postgres"):
            self.assertIn(expected, container)
        for forbidden in ("Rel(app_api, gemini", "Rel(ai_service, postgres", "Rel(app_api, postgres"):
            self.assertNotIn(forbidden, container)

        config = self.read("aact.config.ts")
        self.assertIn("acyclic: true", config)
        self.assertIn("acl: true", config)
        self.assertIn("dbPerService: true", config)

    def test_every_adr_has_cost_and_tests(self) -> None:
        adrs = sorted((ROOT / "docs/adr").glob("ADR-*.md"))
        self.assertGreaterEqual(len(adrs), 3)
        for path in adrs:
            text = path.read_text(encoding="utf-8")
            self.assertIn("## Цена решения", text, path.name)
            self.assertIn("## Как покрыть тестами", text, path.name)

    def test_database_schema_and_migration(self) -> None:
        schema = self.read("database/schema.sql")
        for table in (
            "app_users", "documents", "card_sets", "cards", "study_sessions",
            "answer_attempts", "card_ratings", "ai_call_metrics",
        ):
            self.assertIn(f"CREATE TABLE {table}", schema)
        self.assertIn("text_expires_at", schema)
        self.assertIn("\\ir ../schema.sql", self.read("database/migrations/001_initial.sql"))

    def test_prototype_and_screenshot(self) -> None:
        html = self.read("frontend/prototype/index.html")
        for marker in (
            "Выбрать PDF",
            "Проверить ответ",
            "Полезно",
            "Не по теме",
            "Продолжить",
            "PDF_TEXT_LAYER_REQUIRED",
            "Следующий вопрос",
        ):
            self.assertIn(marker, html)
        for uc in ("uc01", "uc02", "uc03", "uc04-complete", "uc04-resume", "uc05"):
            self.assertIn(f'id="{uc}"', html)
        png = ROOT / "frontend/prototype/screenshots/key-screens.png"
        self.assertTrue(png.is_file())
        with png.open("rb") as file:
            self.assertEqual(file.read(8), b"\x89PNG\r\n\x1a\n")
            length = struct.unpack(">I", file.read(4))[0]
            self.assertEqual(file.read(4), b"IHDR")
            width, height = struct.unpack(">II", file.read(length)[:8])
        self.assertGreaterEqual(width, 1000)
        self.assertGreaterEqual(height, 700)

    def test_compose_has_services_networks_volumes_and_healthchecks(self) -> None:
        compose = self.read("compose.dev.yml")
        for service in ("frontend", "telegram-adapter", "app-api", "data-service", "ai-service", "postgres"):
            self.assertIn(f"  {service}:", compose)
        self.assertGreaterEqual(compose.count("healthcheck:"), 5)
        self.assertIn("internal: true", compose)
        self.assertIn("postgres-data:", compose)

    def test_golden_dataset(self) -> None:
        path = ROOT / "docs/quality/golden-dataset/dataset.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertGreaterEqual(len(rows), 30)
        self.assertEqual(len(rows), len({row["id"] for row in rows}))
        self.assertTrue(all(row["use_case"].startswith("UC-") for row in rows))
        self.assertTrue(all(row["context"] is not None for row in rows))
        non_generation = [row for row in rows if not row["id"].startswith("GEN-")]
        self.assertGreaterEqual(len(non_generation), len(rows) // 3)

    def test_validation_and_sync_are_completed(self) -> None:
        validation = self.read("docs/use-cases/validation.md")
        self.assertIn("Кузнецов", validation)
        self.assertIn("Завершён без вопросов", validation)
        for uc in ("UC-01", "UC-02", "UC-03", "UC-04", "UC-05"):
            self.assertIn(uc, validation)
        self.assertGreaterEqual(validation.count("| да |"), 5)
        sync = self.read("docs/team-sync-lab2.md")
        self.assertIn("согласовано", sync.lower())
        dod = self.read("docs/quality/dod.md")
        self.assertNotIn("- [ ]", dod)
        self.assertIn("0 violations", self.read("docs/architecture/aact-check.md"))
        self.assertIn("200", self.read("docs/architecture/compose-verify.md"))

    def test_quality_documents_cover_requirements(self) -> None:
        dod = self.read("docs/quality/dod.md")
        for role in ("Product / VO", "AI Engineer", "Delivery", "Quality & Safety"):
            self.assertIn(role, dod)
        plan = self.read("docs/quality/test-plan.md")
        for level in ("Unit", "Contract", "Integration", "AI eval", "Security"):
            self.assertIn(level, plan)
        threat = self.read("docs/quality/threat-model.md")
        for index in range(1, 11):
            self.assertIn(f"LLM{index:02d}", threat)
        self.assertIn("права модели", threat.lower())


if __name__ == "__main__":
    unittest.main()
