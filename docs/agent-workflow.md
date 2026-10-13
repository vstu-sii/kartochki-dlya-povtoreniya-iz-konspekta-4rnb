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
- ключ вынесен в `.env`, trace ограничивает preview и не содержит ключа;
- добавлены идемпотентность создания набора, проверка Pydantic и управляемый `503`;
- результат модели сохраняется до ответа UI;
- Compose разделяет internal, edge и egress networks, содержит health checks;
- eval не выдаёт локальную latency и mock/safety guard за облачное измерение.

## Найденные ограничения

1. PDF с текстовым слоем обрабатывается в Telegram Adapter; OCR сканов сознательно оставлен на спринт 4.
2. Создание карточек и проверка ответов доступны через Telegram и браузерный E2E; прогресс Telegram между перезапусками адаптера пока не восстанавливается.
3. Local review agreement 69,05% — `AI-18`; это отражено в Product-отчёте.

## Деплой

`render.yaml` и корневой `Dockerfile` обновляют существующий Render-сервис, а не создают отдельный продукт. В Render нужно выбрать одну Lab3-ветку и задать `GEMINI_API_KEY` только если нужен облачный provider. Без ключа публичный прототип работает на deterministic baseline.

Ожидаемый URL существующего сервиса: https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com. Сам факт обновления URL проверяется отдельно после переключения ветки сервиса; наличие конфигурации в git не выдаётся за выполненный деплой.
