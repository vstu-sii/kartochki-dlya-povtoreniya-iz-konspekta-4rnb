# Передача AI-части

## Контракт

`BaselineModel.generate(payload)` возвращает CardSet со ссылкой на страницу/цитату; `review(payload)` возвращает `correct|partially_correct|incorrect`, score, feedback и missing points. Публичные маршруты описаны в `api/openapi.yaml`.

## Запуск и конфигурация

Без ключа: `MODEL_PROVIDER=deterministic`. С Gemini: `MODEL_PROVIDER=gemini`, секрет `GEMINI_API_KEY`, модели `LLM_PRIMARY_MODEL`/`LLM_CHEAP_MODEL`. Ключи никогда не хранятся в Git. Prompts версионируются в `ml/prompts_v2/`, схемы проверяются до сохранения.

## Путь запроса

API → token budget → source lookup → prompt/schema → Gemini → quality guards → fallback при временном отказе → trace → БД. Модель не пишет в БД и не выполняет необратимых действий; это делает приложение после проверок.

## Проверка

```bash
python tests/evals/run_evals.py --output artifacts/evals/lab5-final-results.json
python tests/evals/run_application_evals.py
python -m ml.experiments.run_ablation
```

Первый прогон подтверждает 95 модельных кейсов и 12 input guards, второй — 37 application/DB-кейсов. Полный командный gate одной командой: `python tests/evals/run_full_suite.py`.

Смотреть: `docs/ml-final-metrics.md`, `docs/experiments/lab5.md`, trace-конфиг `ml/tracing/`. Известные ограничения: один PDF, OCR зависит от качества скана, top-3 retrieval теряет четвёртый релевантный фрагмент, provider A/B мал и требует повторов перед коммерческим SLA.
