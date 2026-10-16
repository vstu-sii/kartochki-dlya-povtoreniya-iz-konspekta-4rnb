# Приёмка инкрементов спринта 4

Приёмка проводится по проверяемому DoD: файл существует, команда воспроизводится, тест или конфигурационная проверка проходит. Устные обещания не считаются принятым результатом.

| Дата | Неделя | Участники | Инкремент | Проверка DoD и свидетельство | Статус | Отклонение / задача | Владелец |
|---|---:|---|---|---|---|---|---|
| 25.09.2026 | 1 | Product, Delivery | MVP scope, PRD v3, budget guard | `docs/mvp-scope.md`; `tests/test_lab4_limits.py` | принято внутри команды | Redis limiter оставлен как оплаченный долг | Product, Delivery |
| 02.10.2026 | 2 | Product, AI, Quality | prompts v2, A/B runner, cache, model tool | `artifacts/experiments/lab4-ab-results.json`; `tests/test_lab4_tool.py` | принято внутри команды | Online A/B требует разрешённого ключа | AI |
| 09.10.2026 | 3 | Product, Delivery, Quality | staging, deploy, dashboard, quality gates | `compose.staging.yml`; `monitoring/`; `.github/workflows/quality-gates.yml` | принято по репозиторному DoD | Production deploy подтверждается только после merge | Delivery |
| 16.10.2026 | 4 | все четыре роли | security v2, критические пути, финальные пороги | `artifacts/security/lab4-attacks-after.json`; `docs/quality/lab4-quality-gates.md` | принято по CI | Новые обходные атаки добавлять в dataset | Quality |

Это внутренний протокол команды: участник означает роль, ответственную за проверку артефакта. Он не подменяет подпись преподавателя или внешнюю приёмку. Для машинной проверки источником факта служит указанный файл и успешный CI run на том же commit SHA.

## Оформленные задачи вместо устных замечаний

- `L4-D-01`, P1, Delivery: вынести limiter в Redis перед масштабированием больше одного backend replica.
- `L4-AI-01`, P1, AI: выполнить разрешённый Gemini A/B и не смешивать его latency с deterministic fallback.
- `L4-Q-01`, P1, Quality: добавить каждый новый production prompt-injection в `tests/security/attacks.jsonl`.
- `L4-P-01`, P2, Product: проверить понятность сообщения о суточном лимите на пяти внешних пользователях.

Финальный статус: инкременты лабораторной 4 приняты по репозиторному DoD; внешняя приёмка преподавателем остаётся отдельным событием.
