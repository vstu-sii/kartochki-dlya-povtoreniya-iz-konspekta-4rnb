# Приёмка инкрементов спринта 4

Приёмка — по проверяемому DoD: файл есть, команда воспроизводится, тест/конфиг проходит. Устные обещания не принимаются. Канон требований: `prd.md` + `use-cases/README.md` (v3) + `mvp-scope.md`.

| Дата | Неделя | Участники | Инкремент | Проверка DoD и свидетельство | Статус | Отклонение / задача | Владелец |
|---|---:|---|---|---|---|---|---|
| 25.09.2026 | 1 | Product, Delivery | MVP scope, PRD v3, UC v3, budget guard (UC-06) | `mvp-scope.md`, `prd.md`, `use-cases/requirements-v3.md`, `tests/test_lab4_limits.py` | принято | Redis limiter — долг `L4-D-01` | Product, Delivery |
| 02.10.2026 | 2 | Product, AI, Quality | prompts v2, локальный algorithm A/B, cache, model tool (UC-07) | `artifacts/experiments/lab4-algorithm-results.json`, `tests/test_lab4_tool.py` | принято | Provider Gemini A/B — `L4-AI-01`, закрыто 17.10 | AI |
| 09.10.2026 | 3 | Product, Delivery, Quality | staging, deploy, dashboard, quality gates | `compose.staging.yml`, `monitoring/`, `.github/workflows/quality-gates.yml` | принято | Prod deploy подтверждается после merge — Delivery | Delivery |
| 16.10.2026 | 4 | все роли | security v2, критические пути, финальные пороги, sync UC README | `artifacts/security/lab4-attacks-after.json`, `use-cases/README.md` v3 | принято | Новые injection → dataset `L4-Q-01` | Quality |

## Задачи вместо устных замечаний

- `L4-D-01`, P1, Delivery: Redis limiter перед >1 backend replica.
- `L4-AI-01`, P1, AI — **закрыто 17.10.2026**: официальный Google Gemini API, 20 кейсов и 40 вызовов; prompt A — 95%, prompt B — 100%, выбран B. Свидетельство: `artifacts/experiments/lab4-provider-results.json` в ветке `lab4-ai-infrastructure`, коммит `edef5df`.
- `L4-Q-01`, P1, Quality: каждый новый prod injection → `tests/security/attacks.jsonl`.
- `L4-P-01`, P2, Product: проверить понятность сообщения о суточном лимите (UC-06) на 5 внешних пользователях.

## Закрытие AI-отклонения после финальной контрольной точки

17.10.2026 команда получила разрешённый provider-прогон через официальный Google Gemini API. Использована `gemini-3.5-flash-lite`, поскольку дневная free-tier квота основной `gemini-3.8-flash` была исчерпана. На одинаковых 20 кейсах и при одинаковых schema/параметрах prompt B дал 100% против 95% у A. Цена решения — 6 380 токенов против 3 843 (+66%). Результат относится только к фактически использованной модели и не выдаётся за замер `gemini-3.8-flash`.

## DoD Product Lab 4 — итог приёмки

| Критерий | Статус | Свидетельство |
|---|---|---|
| Burndown весь спринт | принято | `burndown.md` (бэклог 42 SP + график) |
| MVP-скоуп + вырезанное с причинами | принято | `mvp-scope.md` |
| Еженедельные приёмки | принято | этот файл |
| Требования v3 | принято | `prd.md`, `use-cases/README.md`, `requirements-v3.md` |

Финальный статус: инкременты Lab 4 приняты по репозиторному DoD. Внешняя приёмка преподавателем — отдельное событие.
