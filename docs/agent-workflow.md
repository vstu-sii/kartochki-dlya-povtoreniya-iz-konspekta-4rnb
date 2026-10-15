# Отчёт агентной разработки Lab 3

## Что было сгенерировано

- каркас FastAPI Application API и AI Service;
- ORM-модели и SQL-миграция;
- настоящий Telegram Adapter с PDF, карточками, ответами и inline-кнопкой;
- web-прототип для воспроизводимого E2E с loading/error states;
- Compose-контур из PostgreSQL, backend, AI, frontend и tracing dashboard;
- deterministic eval runner и GitHub Actions jobs.

## Что проверено и исправлено человеком

- API сохранён совместимым с OpenAPI лабы 2: `card-sets` и `answer-reviews`;
- недоверенный текст помещён только в CONTEXT, модель не получает инструментов;
- ключ вынесен в `.env`; по умолчанию trace хранит хеш и метрики без текста PDF;
- добавлены идемпотентность создания набора, проверка Pydantic и управляемый `503`;
- результат модели сохраняется до ответа UI;
- Compose разделяет internal, edge и egress networks, содержит health checks;
- eval не выдаёт локальную latency и mock/safety guard за облачное измерение;
- отдельный `run_application_evals.py` исполняет все 33 немодельных кейса через настоящие guard-, router- и ORM-функции; JSON-результат загружается из CI.

## Найденные ограничения

1. Текстовые PDF читаются напрямую, для страниц-сканов включается OCR `rus+eng`.
2. Создание карточек и смысловая проверка ответов доступны через Telegram; прогресс восстанавливается из БД после `/start`.
3. Gemini используется как основной provider, но при лимите или ошибке автоматически включается локальный grounded baseline.
4. Бесплатный Gemini предназначен для демо/пилота; перед коммерческой обработкой приватных документов нужен оплачиваемый тариф и юридическая политика.

## Воспроизведение API/DB evals

```bash
python tests/evals/run_application_evals.py
```

Ожидаемый результат: `33/33`, отчёт — `artifacts/evals/application-results.json`. Это отдельная метрика от модельных 95 кейсов.

## Деплой

`render.yaml` и корневой `Dockerfile` обновляют существующий Render-сервис. В Render
нужно выбрать Delivery-ветку и задать два секрета: `TELEGRAM_BOT_TOKEN` и
`GEMINI_API_KEY`. Без ключа Gemini публичный прототип продолжит работать на
deterministic baseline, но смысловая проверка будет менее точной.

Ожидаемый URL существующего сервиса: https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com. Сам факт обновления URL проверяется отдельно после переключения ветки сервиса; наличие конфигурации в git не выдаётся за выполненный деплой.
