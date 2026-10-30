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
- prompt contract: 100% шаблонов рендерятся; отдельно выполнен настоящий Gemini prompt-only A/B на 20 кейсах (`artifacts/experiments/lab4-provider-results.json`);
- curated retrieval: hit@1 100%, recall@3 100% на 10 синтетических кейсах;
- production query builder: метрики записаны отдельно в retrieval artifact;
- coverage probe показывает потерю страниц 4–5 при фиксированном top-3.

## Проверки

- `tests/test_lab4_tool.py`: success/forbidden/empty/error, настоящий timeout, fallback, cache и trace;
- `tests/test_lab4_limits.py`: 80%, hard limit, reset, usage и TTL;
- CI: compile/import, unit/integration, retrieval, algorithm regression и prompt contract.

## Оставшиеся ограничения

Gemini prompt A/B выполнен один раз на 20 кейсах и не заменяет полный deterministic gate. Top-3 может потерять важный факт длинного документа. Cache и limiter process-local. Provider p95 6849,14 мс измерен на малой выборке и не является production SLA.
