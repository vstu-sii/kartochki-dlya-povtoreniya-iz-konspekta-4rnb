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

Telegram Adapter входит в тот же Compose. Без токена он запускается в безопасном
режиме ожидания, чтобы проверка проекта не зависела от секретов. Для настоящего
бота создайте токен через BotFather и задайте `TELEGRAM_BOT_TOKEN` в локальном
`.env` или в секретах прод-сервиса. После этого бот принимает PDF до 10 МБ,
создаёт карточки, показывает источник, проверяет ответы и переключает карточки.
Оценки «полезно/не полезно» и текущая позиция сохраняются в БД; после `/start`
бот продолжает последнюю незавершённую сессию.
Локально адаптер использует long polling; на Render backend автоматически
регистрирует защищённый webhook на `RENDER_EXTERNAL_URL`, поэтому сервису не
нужно постоянно опрашивать Telegram.

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
| Telegram Adapter | `telegram_bot/` | PDF из Telegram, карточки, ответы и кнопки |
| Web-клиент | `frontend/prototype/` | браузерный E2E, loading/error states, карточка и review |
| Application API | `backend/` | валидация, async-вызов AI, идемпотентность, сохранение |
| Baseline | `ml/models/baseline.py` | structured cards/review, retry и fallback |
| Trace SDK/dashboard | `ml/tracing/` | prompt, response, model, latency и fallback каждого вызова |
| БД | `backend/models/`, `migrations/` | documents, card sets, cards, reviews, study sessions, ratings |
| Evals | `tests/evals/`, `.github/workflows/evals.yml` | mini/full прогоны и порог CI |
| Product validation | `docs/use-cases/validation-lab3.md` | E2E, отклонения, задачи и владельцы |

## Ограничения текущего прототипа

- PDF должен содержать текстовый слой; OCR сканов оставлен на следующий спринт;
- история изменений оценки не хранится: повторная оценка заменяет текущее значение;
- автоматическое удаление учебных сессий через 30 дней оставлено на следующий спринт;
- локальный baseline имеет 69,05% agreement review и не выдаётся за качество Gemini;
- `render.yaml` обновляет существующий Render-сервис, а не создаёт новый продукт.

Правила работы команды: `CONTRIBUTING.md`. Полный отчёт ограничений: `docs/iteration-notes.md`.
