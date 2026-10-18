# Lab4 — Quality & Safety

Актуальная проверка всей роли:

```bash
python -m pip install -r backend/requirements.txt
python tests/evals/run_full_suite.py
```

Нужен Git checkout с историей коммита Lab3 для воспроизводимого security-before.
В CI используется Python 3.11 и fetch-depth: 0. Все модельные измерения локальные, без ключа Gemini.

**Статус повторного локального прогона 17.10.2026: gate зелёный.** Все 132 уникальных golden-кейса исполняются; application 37/37, security after 14/14, unit/integration 29/29. Таймаут инструмента, ATK-011 и повтор без identity закрыты точечными runtime-исправлениями и теми же регрессионными сценариями. Успешные удалённые проверки коммита `3760914`: [Lab4 full quality gates](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/38959398688) и [Lab4 CI](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/38959398794). Локальный и CI-прогоны не являются подтверждением production-среды.

- [Пороги, команды и результаты](docs/quality/lab4-quality-gates.md)
- [Актуальный eval-отчёт и исторический baseline](docs/quality/eval-report-1.md)
- [Открытые дефекты, владельцы и критерии закрытия](docs/quality/open-findings-lab4.md)
- [Security before](docs/quality/security-report-1.md) / [after](docs/quality/security-report-2.md)

В GitHub Actions можно вручную запустить **Lab4 full quality gates**.
Даже при провале сохраняются JSON и логи всех наборов. Запрет merge требует назначения
full-evals обязательной проверкой в настройках GitHub; наличие workflow само по себе этого не гарантирует.

Ниже сохранена общая инструкция запуска прототипа предыдущей версии; она не является
доказательством production-ready или закрытия перечисленных проблем.

---


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
`.env` или в секретах прод-сервиса. После этого бот принимает PDF до 10 МБ и
40 страниц, извлекает текст (для сканов использует OCR), создаёт карточки,
показывает подтверждающую цитату и проверяет ответы по смыслу. Синонимы и
формулировки своими словами разрешены — ответ не обязан совпадать с эталоном дословно.
Оценки «полезно/не полезно» и текущая позиция сохраняются в БД; после `/start`
бот продолжает последнюю незавершённую сессию.
Локально адаптер использует long polling; на Render backend автоматически
регистрирует защищённый webhook на `RENDER_EXTERNAL_URL`, поэтому сервису не
нужно постоянно опрашивать Telegram.

Остановка с сохранением БД: `docker compose -f compose.yml down`. Полная очистка демонстрационных данных: `docker compose -f compose.yml down -v`.

## Бесплатная модель Gemini

1. Получите API-ключ в [Google AI Studio](https://aistudio.google.com/apikey).
2. Скопируйте `.env.example` в `.env`.
3. Заполните `GEMINI_API_KEY` и оставьте `MODEL_PROVIDER=gemini`.
4. Запустите Compose командой выше.

Используется `gemini-3.8-flash` с JSON Schema. Для каждого запроса есть до трёх
попыток; при лимите, сетевой ошибке или некорректном ответе включается локальный
grounded baseline, поэтому бот не перестаёт работать. Ключи и `.env` не попадают
в Git. Бесплатный тариф подходит для демонстрации и раннего пилота, но имеет
лимиты. Кроме того, согласно условиям Google, данные бесплатного тарифа могут
использоваться для улучшения продуктов. Для коммерческой работы с приватными
учебными материалами нужен оплачиваемый тариф и политика обработки данных.

## Проверки

```bash
python -m unittest discover -s tests -p "test_*.py"
python tests/evals/run_application_evals.py
docker compose -f compose.yml config --quiet
```

Application eval пишет `artifacts/evals/application-results.json`. CI дополнительно
запускает unit-тесты, собирает Compose, ждёт health checks и проверяет сквозной
путь UI → API → модель → БД.

## Состав системы

| Компонент | Путь | Ответственность |
|---|---|---|
| Telegram Adapter | `telegram_bot/` | PDF из Telegram, карточки, ответы и кнопки |
| Web-клиент | `frontend/prototype/` | браузерный E2E, loading/error states, карточка и review |
| Application API | `backend/` | валидация, async-вызов AI, идемпотентность, сохранение |
| Baseline | `ml/models/baseline.py` | structured cards/review, retry и fallback |
| Trace SDK/dashboard | `ml/tracing/` | хеш/размер запроса, model, latency, usage и fallback; текст скрыт по умолчанию |
| БД | `backend/models/`, `migrations/` | documents, card sets, cards, reviews, study sessions, ratings |
| Evals | `tests/evals/`, `.github/workflows/evals.yml` | mini/full прогоны и порог CI |
| Product validation | `docs/use-cases/validation-lab3.md` | E2E, отклонения, задачи и владельцы |

## Границы готовности

- карточки grounded: каждая содержит страницу и дословную цитату из PDF;
- ответ Gemini проходит строгую JSON-схему и серверную проверку grounding;
- трассы по умолчанию не содержат текст PDF (`TRACE_CONTENT=false`);
- прогресс и история оценок сохраняются, незавершённая сессия восстанавливается;
- сессии старше 30 дней не открываются;
- `render.yaml` обновляет существующий Render-сервис, а не создаёт новый продукт;
- перед реальными продажами выполните чек-лист `docs/production-readiness.md`.

Правила работы команды: `CONTRIBUTING.md`. Полный отчёт ограничений: `docs/iteration-notes.md`.
