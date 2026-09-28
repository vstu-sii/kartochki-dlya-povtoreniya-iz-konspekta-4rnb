# Проверка aact — лабораторная 2

**Дата:** 2026-09-28  
**Источник диаграммы:** `docs/architecture/c4-container.puml`  
**Конфиг:** `aact.config.ts`

## Команды

```bash
# официальная проверка курса (когда доступен npm)
npx aact@beta check

# локальный эквивалент правил репозитория (без npm)
python -m unittest tests.test_aact_local -v
```

## Результат

Локальная проверка правил `acyclic`, `acl`, `dbPerService` и разметки ACL/repo:

| Правило | Ожидание | Факт |
|---|---|---|
| acyclic | нет циклов между контейнерами | 0 нарушений |
| acl | Telegram/Gemini только через ACL | 0 нарушений |
| dbPerService | PostgreSQL только у Data Service | 0 нарушений |
| tags | ≥2 acl, ≥1 repo | выполнено |

Извлечённые связи:

`student → telegram → telegram_adapter → app_api → {ai_service, data_service}`; `data_service → postgres`; `ai_service → gemini`.

**Итог: 0 violations.**

Официальный `npx aact@beta check` использует тот же PlantUML-источник и тот же конфиг. В среде без Node/npm команда курса не запускалась; машинная проверка границ закрыта локальным тестом `tests/test_aact_local.py`, который входит в `python -m unittest discover -s tests -p "test_*.py"`.
