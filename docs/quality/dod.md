# Definition of Done — лабораторная 2

Статусы: `[x]` выполнено и проверено. Согласование команды: `docs/team-sync-lab2.md` (2026-09-28).

## Product / VO

- [x] `docs/use-cases/README.md`: пять UC содержат актёра, цель, контекст, шаги, результат, исключения и измеримый критерий.
- [x] `docs/use-cases/use-cases.puml`: диаграмма PlantUML лежит в репозитории.
- [x] `docs/use-cases/validation.md`: UC-01…UC-05 прожиты человеком не из команды без вопросов; таблица заполнена.
- [x] `docs/roadmap.md`: MVP, явный не-скоуп и вехи до Demo Day.
- [x] `docs/glossary.md`: термины архитектуры и AI-пайплайна; ≥30 терминов.
- [x] Глоссарий и roadmap согласованы командой вслух — `docs/team-sync-lab2.md`.
- [x] `docs/adr/`: только структурные решения; в каждом есть «Цена решения» и тестируемость.

## AI Engineer

- [x] `docs/ai-pipeline.md`: PlantUML, этапы, промпты, primary/fallback, quality gates, logging и границы контекста.
- [x] `docs/model-candidates.md`: финальный выбор, стоимость, дешёвая деградация и «Цена решения».
- [x] `docs/experiments/lab2.md`: риски названы; два спайка с вопросом, методом и честным результатом.
- [x] `notebooks/lab2_spikes.ipynb`: валидный notebook с сохранёнными результатами.
- [x] `api/openapi.yaml`: OpenAPI 3.1, два endpoint, строгие CardSet/AnswerReview и стабильные ошибки.
- [x] Допущения A1/A2 проверены спайками. Полный прогон Gemini на 10 PDF (A3–A5) зафиксирован как вход лабы 3 в `docs/experiments/lab2.md` — без ключа пороги качества не заявляются.

## Delivery

- [x] `docs/architecture/c4-context.puml` и `c4-container.puml`: уровни не смешаны, связи подписаны.
- [x] `aact.config.ts`: применимые правила включены, отключённые объяснены.
- [x] Официальный `aact@beta check` и `tests/test_aact_local.py` → **0 violations**; протокол в `docs/architecture/aact-check.md`.
- [x] `frontend/prototype/`: UI всех UC-01…UC-05 и актуальный скриншот `screenshots/key-screens.png`.
- [x] `database/schema.sql`, `database/migrations/001_initial.sql`, `docs/architecture/erd.puml` согласованы.
- [x] `compose.dev.yml`: сервисы, networks, egress AI Service, volume, health checks; CI поднимает Compose с `--wait` и проверяет UI HTTP 200.

## Quality & Safety

- [x] Этот DoD покрывает каждый артефакт проверяемыми критериями.
- [x] DoD согласован Product и всей командой — `docs/team-sync-lab2.md`.
- [x] `docs/quality/golden-dataset/dataset.jsonl`: 36 пар, покрытие UC-01…UC-05, краевые и security-кейсы.
- [x] `docs/quality/golden-dataset/README.md`: происхождение, формат, владелец, версия, процесс изменения.
- [x] `docs/quality/test-plan.md`: unit, contract, integration, eval, security, нагрузка и CI-план.
- [x] `docs/quality/threat-model.md`: точки недоверенного ввода, OWASP LLM Top 10, права модели, атаки лабы 4.

## Общая автоматическая проверка

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Дополнительно при наличии Docker/npm:

```bash
docker compose -f compose.dev.yml config
docker compose -f compose.dev.yml up --build
npx aact@beta check
```

**Статус лабораторной 2:** Definition of Done выполнен. Чертежи готовы к PR по ролям.
