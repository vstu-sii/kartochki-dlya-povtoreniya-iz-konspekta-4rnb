# Архитектура лабораторной 2

| Файл | Содержание |
|---|---|
| `c4-context.puml` | Система, актёр и внешние зависимости |
| `c4-container.puml` | Контейнеры и хранилище; источник для aact |
| `erd.puml` | Логическая схема данных |
| `aact-check.md` | Результат проверки границ: 0 violations |
| `compose-verify.md` | Проверка compose-скелета и health stubs |

Архитектурные решения и поле «Цена решения»: `docs/adr/`.

Рендеринг:

```bash
plantuml -tsvg docs/architecture/*.puml
```

Проверка границ:

```bash
python -m unittest tests.test_aact_local -v
npx aact@beta check
```

`aact.config.ts` включает `acyclic`, `acl`, `dbPerService`, `commonReuse` и объясняет отключённые правила. Актуальный вердикт: **0 violations** (`aact-check.md`).
