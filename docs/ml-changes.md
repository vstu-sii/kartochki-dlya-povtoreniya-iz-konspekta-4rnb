# Изменения AI-части за спринт 4

## Пайплайн

- Prompt v1 и v2 хранятся файлами в `ml/prompts_v2/`; версии берутся из единственного `versions.json`.
- `run_ab.py` разделяет локальное A/B алгоритмов, provider-free contract check и настоящий prompt-only provider A/B.
- TTL-кэш возвращает копию результата без повторного provider call; cache hit виден в trace.
- Application limiter выбирает cheap tier после 80% и полностью запрещает вызов после дневного лимита.
- `lookup_source` разрешает только данные владельца, возвращает до трёх фрагментов и имеет статусы `success`, `timeout`, `forbidden`, `error`, `empty`.

## Таймаут и fallback

Вызовы идут через общий пул из четырёх потоков и восемь bounded slots. На deadline внешний вызов возвращает `timeout`, а генерация использует исходные страницы. Исключение даёт `error`, чужой владелец — `forbidden`, отсутствие совпадений — `empty`; все четыре состояния безопасно переходят к исходным страницам. Лог содержит только status, elapsed_ms, cache_hit и код — без запроса и PDF.

Ограничение: Python не может принудительно остановить уже выполняющийся поток. После timeout операция заканчивается в фоне; bounded pool не даёт создавать неограниченное число таких задач. Для жёсткого уничтожения зависшего native call потребуется отдельный процесс или внешний сервис.

## Фактические метрики

- algorithm A/B: 82,5% против 90,0%; это алгоритмы, не prompts;
- prompt contract: 100% шаблонов рендерятся;
- Gemini prompt A/B на 20 кейсах: v1 — 95%, v2 — 100%, прирост +5 п.п.; выбран v2;
- цена v2 на этом прогоне: 6 380 токенов против 3 843 у v1 (+66%);
- curated retrieval: hit@1 100%, recall@3 100% на 10 синтетических кейсах;
- production query builder: метрики записаны отдельно в retrieval artifact;
- coverage probe показывает потерю страниц 4–5 при фиксированном top-3.

## Проверки

- `tests/test_lab4_tool.py`: success/forbidden/empty/error, настоящий timeout, fallback, cache и trace;
- `tests/test_lab4_limits.py`: 80%, hard limit, reset, usage и TTL;
- CI: compile/import, unit/integration, retrieval, algorithm regression и prompt contract.

## Оставшиеся ограничения

Prompt A/B выполнен на `gemini-3.5-flash-lite`, а не на основной `gemini-3.8-flash`, потому что дневная free-tier квота основной модели была исчерпана. Результат нельзя автоматически переносить на другую модель. Top-3 может потерять важный факт длинного документа. Cache и limiter process-local. Локальные latency не являются production SLA.
