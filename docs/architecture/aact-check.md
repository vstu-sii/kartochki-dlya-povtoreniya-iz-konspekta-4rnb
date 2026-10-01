# Проверка aact — лабораторная 2

**Источник диаграммы:** `docs/architecture/c4-container.puml`  
**Конфиг:** `aact.config.ts`

## Команды

```bash
# официальная проверка курса
npx aact@beta check

# локальный эквивалент правил репозитория (без npm)
python -m unittest tests.test_aact_local -v
```

## Результат

Официальная проверка `aact@3.0.0-beta.29` и локальная проверка правил `acyclic`, `acl`, `dbPerService` и ACL/repo:

| Правило | Ожидание | Факт |
|---|---|---|
| acyclic | нет циклов между контейнерами | 0 нарушений |
| acl | Telegram/Gemini только через ACL | 0 нарушений |
| dbPerService | PostgreSQL только у Data Service | 0 нарушений |
| tags | ≥2 acl, ≥1 repo | выполнено |

Извлечённые связи:

`student → telegram_adapter`; `telegram → telegram_adapter → app_api → {ai_service, data_service}`; `data_service → postgres`; `ai_service → gemini`.

**Итог официальной команды: `No violations found` (0 violations).**

Конфиг использует тип `AactConfig`, поэтому загружается как через `npx`, так и в CI. Локальный тест `tests/test_aact_local.py` оставлен как быстрая дополнительная проверка.
