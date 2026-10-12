# Карточки для повторения — Lab 3 MVP

Рабочий прототип подготовки к устной защите: интерфейс отправляет учебный текст в API, AI Service создаёт grounded-карточки, Application API сохраняет их в PostgreSQL, а dashboard показывает каждый модельный вызов.

## Запуск одной командой

```bash
docker compose -f compose.yml up --build --wait
```

После запуска:

- приложение: http://localhost:8080;
- OpenAPI backend: http://localhost:8080/api/docs;
- трассировка prompt/response: http://localhost:3000;
- health: `docker compose -f compose.yml ps` — все сервисы `healthy`.

Остановка с сохранением БД: `docker compose -f compose.yml down`. Полная очистка демонстрационных данных: `docker compose -f compose.yml down -v`.

Ключ не обязателен: по умолчанию работает deterministic grounded baseline. Для Gemini скопируйте `.env.example` в `.env`, задайте `MODEL_PROVIDER=gemini` и `GEMINI_API_KEY`. `.env` исключён из git.

## Проверки

```bash
python -m unittest discover -s tests -p "test_*.py"
python tests/evals/run_evals.py --mini --fail-below 0.90
python tests/evals/run_evals.py
docker compose -f compose.yml config --quiet
```

Полный eval пишет `artifacts/evals/baseline-results.json`, включая latency и токены. CI дополнительно собирает Compose, ждёт health checks и запрашивает UI.

## Состав системы

| Компонент | Путь | Ответственность |
|---|---|---|
| Web/Telegram storyboard | `frontend/prototype/` | ввод, loading/error states, карточка и review |
| Application API | `backend/` | валидация, async-вызов AI, идемпотентность, сохранение |
| Baseline | `ml/models/baseline.py` | structured cards/review, retry и fallback |
| Trace SDK/dashboard | `ml/tracing/` | prompt, response, model, latency и fallback каждого вызова |
| БД | `backend/models/`, `migrations/` | documents, card sets, cards, reviews |
| Evals | `tests/evals/`, `.github/workflows/evals.yml` | mini/full прогоны и порог CI |
| Product validation | `docs/use-cases/validation-lab3.md` | E2E, отклонения, задачи и владельцы |

## Ограничения текущего прототипа

- текстовый слой PDF пока вставляется вручную; это записанная задача `DELIVERY-14`;
- rating/resume ещё не доведены до UI (`DELIVERY-15/16`);
- локальный baseline имеет 69,05% agreement review и не выдаётся за качество Gemini;
- `render.yaml` готовит обновление существующего Render-сервиса, но публичный URL считается подтверждённым только после фактического переключения ветки в Render.

Правила работы команды: `CONTRIBUTING.md`. Полный отчёт ограничений: `docs/iteration-notes.md`.
