# Lab 3: цифры baseline и выводы

## Как воспроизвести

```bash
python tests/evals/run_evals.py --output artifacts/evals/baseline-results.json
```

Команда не требует сети и ключа. Она читает frozen JSONL, вызывает тот же `BaselineModel`, который доступен через API, пишет результаты, latency, токены и отдельный trace-файл. Ноутбук `notebooks/lab3_baseline.ipynb` выполняет эту же команду и читает артефакт, поэтому цифры не остаются только в выводе ячейки.

## Зафиксированный прогон 12.10.2026

- 128 уникальных кейсов, из них 93 модельных (`generate_card`/`review_answer`);
- schema pass rate: **100%**;
- grounded-card rate: **100%**;
- agreement review с эталоном: **69,05%**;
- формальные safety guards: **100%**;
- p50/p95 локального вызова: **1/1 мс**;
- оценка токенов: **5 905 входных / 35 215 выходных**.

Источник истины: `artifacts/evals/baseline-results.json`. Числа в документе округлены.

## Что означают цифры для продукта

Baseline доказывает техническую концепцию: структура стабильна, цитаты проверяемы, ответы проходят весь путь и трассируются. Он **не готов** оценивать знания пользователя: примерно три из десяти review расходятся с человеческим эталоном. Локальную latency нельзя выдавать за latency Gemini.

Решение: сохранить deterministic baseline как дешёвый CI fallback; на следующем шаге прогнать primary Gemini на том же наборе и принять её только при agreement review ≥85%, grounding ≥95%, p95 review ≤7 секунд и стоимости ≤$0.04 за сессию. Ошибки partial/incorrect из `docs/quality/eval-report-1.md` идут в prompt tuning первыми.

## Retry, fallback и трассировка

При `MODEL_PROVIDER=gemini` выполняется один повтор сетевого вызова; после повторного сбоя используется grounded deterministic fallback. В ответе фиксируются `model`, `fallback_used`, `trace_id`, latency и usage. Каждый вызов записывается SDK `ml/tracing/client.py`; dashboard доступен на порту 3000. Ключ читается только из `GEMINI_API_KEY`.
