# Финальный отчёт качества Lab 5

## Release candidate 18.10.2026

Команда `python tests/evals/run_release_evals.py --release-ref WORKTREE` запустила восемь групп. Все завершились с code 0; объединённое покрытие — **132/132** уникальных кейса, пропусков нет. Двенадцать security-кейсов намеренно проверены и model-, и application-runner; это перекрёстная проверка, а не недостающее покрытие. Это локальная release candidate: после разрешённого коммита тот же runner обязан зелёным пройти на теге `v0.5.0`.

| Метрика | Lab 3 | Lab 4 / Lab 5 RC | Порог | Итог |
|---|---:|---:|---:|---|
| Schema validity | 100% | 100% | 100% | зелёный |
| Grounding | 100% | 100% | 100% | зелёный |
| Review agreement | 90,48% | 90,48% | ≥85% | зелёный, плато |
| Safety guard | не измерен baseline runner | 100% | 100% | зелёный |
| Application E2E | 33 пропущено | 37/37 | 100% | закрыт разрыв |
| Retrieval hit@1 / recall@3 | не было | 100% / 100% | ≥90% / 100% | зелёный |

Источник: `artifacts/evals/lab4-full-results.json`, `application-results.json`, `full-suite-results.json`, `artifacts/experiments/lab4-retrieval-results.json`. Локальная p95 модели (2 мс) — скорость deterministic-кода, не Gemini.

## Ограничения

- Gemini prompt A/B — 20 кейсов и один повтор на `gemini-3.5-flash-lite`; полный релизный gate deterministic.
- Golden dataset в основном synthetic/team-curated, внешняя разметка мала.
- Top-3 retrieval теряет четвёртый релевантный фрагмент.
- Бинарный PDF parser/OCR не входит в 14 HTTP security-сценариев.
- North Star имеет n=1 и пока не подтверждает продуктовую цель статистически.
