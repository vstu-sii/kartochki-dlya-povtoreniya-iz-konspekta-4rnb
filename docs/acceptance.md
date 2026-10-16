# Приёмка инкрементов спринта 4

Приёмка — по проверяемому DoD: файл есть, команда воспроизводится, тест/конфиг проходит. Устные обещания не принимаются. Канон требований: `prd.md` + `use-cases/README.md` (v3) + `mvp-scope.md`.

| Дата | Неделя | Участники | Инкремент | Проверка DoD и свидетельство | Статус | Отклонение / задача | Владелец |
|---|---:|---|---|---|---|---|---|
| 25.09.2026 | 1 | Product, Delivery | MVP scope, PRD v3, UC v3, budget guard (UC-06) | `mvp-scope.md`, `prd.md`, `use-cases/requirements-v3.md`, `tests/test_lab4_limits.py` | принято | Redis limiter — долг `L4-D-01` | Product, Delivery |
| 02.10.2026 | 2 | Product, AI, Quality | prompts v2, A/B, cache, model tool (UC-07) | `artifacts/experiments/lab4-ab-results.json`, `tests/test_lab4_tool.py` | принято | Online Gemini A/B — `L4-AI-01` | AI |
| 09.10.2026 | 3 | Product, Delivery, Quality | staging, deploy, dashboard, quality gates | `compose.staging.yml`, `monitoring/`, `.github/workflows/quality-gates.yml` | принято | Prod deploy подтверждается после merge — Delivery | Delivery |
| 16.10.2026 | 4 | все роли | security v2, критические пути, финальные пороги, sync UC README | `artifacts/security/lab4-attacks-after.json`, `use-cases/README.md` v3 | принято | Новые injection → dataset `L4-Q-01` | Quality |

## Задачи вместо устных замечаний

- `L4-D-01`, P1, Delivery: Redis limiter перед >1 backend replica.
- `L4-AI-01`, P1, AI: разрешённый Gemini A/B; не смешивать latency с deterministic.
- `L4-Q-01`, P1, Quality: каждый новый prod injection → `tests/security/attacks.jsonl`.
- `L4-P-01`, P2, Product: проверить понятность сообщения о суточном лимите (UC-06) на 5 внешних пользователях.

## DoD Product Lab 4 — итог приёмки

| Критерий | Статус | Свидетельство |
|---|---|---|
| Burndown весь спринт | принято | `burndown.md` (бэклог 42 SP + график) |
| MVP-скоуп + вырезанное с причинами | принято | `mvp-scope.md` |
| Еженедельные приёмки | принято | этот файл |
| Требования v3 | принято | `prd.md`, `use-cases/README.md`, `requirements-v3.md` |

Финальный статус: инкременты Lab 4 приняты по репозиторному DoD. Внешняя приёмка преподавателем — отдельное событие.
