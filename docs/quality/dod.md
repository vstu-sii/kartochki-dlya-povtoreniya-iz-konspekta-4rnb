# Definition of Done — лабораторная 2

Статусы: `[x]` — артефакт подготовлен и для него задан проверяемый критерий. Согласование команды: `docs/team-sync-lab2.md` (2026-10-01).

## Product / VO

- [x] `docs/use-cases/README.md`: пять UC содержат актёра, цель, контекст, шаги, результат, исключения и измеримый критерий.
- [x] `docs/use-cases/use-cases.puml`: диаграмма PlantUML лежит в репозитории.
- [x] `docs/use-cases/validation.md`: UC-01…UC-05 прожиты человеком не из команды без вопросов; таблица заполнена.
- [x] `docs/roadmap.md`: MVP, явный не-скоуп и вехи до Demo Day.
- [x] `docs/glossary.md`: термины архитектуры и AI-пайплайна; ≥30 терминов.
- [x] Глоссарий и roadmap согласованы командой — `docs/team-sync-lab2.md`.
- [x] `docs/adr/`: только структурные решения; в каждом есть «Цена решения» и тестируемость.

## AI Engineer

- [x] `docs/ai-pipeline.md`: PlantUML показывает путь запроса от входа до ответа, primary/fallback, quality gates, logging и границы контекста.
- [x] `docs/model-candidates.md`: финальный выбор обоснован сравнением; названы стоимость, дешёвая деградация и «Цена решения».
- [x] `docs/experiments/lab2.md`: указаны проверяемые допущения, методы, результаты и принятые решения.
- [x] `notebooks/lab2_spikes.ipynb`: валидный notebook с сохранёнными результатами.
- [x] `docs/architecture/erd.puml`: ERD находится в ветке роли Модель и согласован с контрактом данных.
- [x] `api/openapi.yaml`: OpenAPI 3.1, два endpoint, строгие CardSet/AnswerReview и стабильные ошибки.
- [x] Допущения A1/A2 проверены спайками. Полный прогон Gemini на 10 PDF (A3–A5) зафиксирован как вход лабораторной 3 в `docs/experiments/lab2.md`; без ключа пороги качества не заявляются.

## Delivery

- [x] `docs/architecture/c4-context.puml` и `docs/architecture/c4-container.puml`: уровни не смешаны, связи подписаны.
- [x] `aact.config.ts`: применимые правила включены, отключённые объяснены.
- [x] Официальный `npx aact@beta check` возвращает **0 violations**; команда и результат зафиксированы в `docs/architecture/aact-check.md`.
- [x] `frontend/prototype/`: интерфейс Telegram-бота покрывает UC-01…UC-05; актуальный скриншот находится в `screenshots/key-screens.png`.
- [x] `database/schema.sql`, `database/migrations/001_initial.sql` и `docs/architecture/erd.puml` используют согласованные сущности и связи.
- [x] `compose.dev.yml`: описаны заглушки сервисов, networks, egress AI Service, volume и health checks; приёмка выполняется командой `docker compose -f compose.dev.yml up --build --wait`, после которой UI должен отвечать HTTP 200.

## Quality & Safety

- [x] Этот DoD покрывает артефакты всех ролей проверяемыми условиями «да/нет».
- [x] DoD согласован Product и командой — `docs/team-sync-lab2.md`.
- [x] `docs/quality/golden-dataset/dataset.jsonl`: 120 уникальных пар, покрытие UC-01…UC-05, краевые и security-кейсы; поднаборы имеют заявленный минимальный объём.
- [x] `docs/quality/golden-dataset/README.md`: происхождение, формат, владелец, версия и процесс изменения набора.
- [x] `docs/quality/test-plan.md`: unit, contract, integration, eval, security, нагрузка и перечень проверок CI.
- [x] `docs/quality/threat-model.md`: точки недоверенного ввода, OWASP LLM Top 10, права модели и запланированные атаки лабораторной 4.

## Команды приёмки

При наличии Node.js/npm:

```bash
npx aact@beta check
```

При наличии работающего Docker Engine:

```bash
docker compose -f compose.dev.yml config
docker compose -f compose.dev.yml up --build --wait
```

После запуска Compose интерфейс проверяется по адресу `http://localhost:8080`; ожидается HTTP 200.

**Статус лабораторной 2:** обязательные артефакты подготовлены по ролям. Проверки, которым требуется Docker/npm, выполняются на машине с доступным Docker Engine и Node.js.
