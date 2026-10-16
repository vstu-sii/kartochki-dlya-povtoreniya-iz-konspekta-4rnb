# Отдельный замер поиска по документу

`lookup_source` измеряется отдельно от качества итогового ответа:

```bash
python -m ml.experiments.run_retrieval_eval --min-hit-at-1 .90 --min-recall-at-3 1.0
```

Набор `tests/evals/retrieval-cases.jsonl` содержит запрос, три конкурирующих фрагмента и ожидаемую страницу. Прогон считает hit rate@1, recall@3, MRR и p50/p95 latency. Машиночитаемый результат сохраняется в `artifacts/experiments/lab4-retrieval-results.json` и проверяется в CI. Это не подменяется метрикой grounding: поиск отвечает на вопрос «нашёл ли правильный фрагмент», grounding — «не выдумал ли ответ поверх найденного».

Источник истины для конкретного прогона — JSON-артефакт на том же commit SHA. Этот offline-набор проверяет текущий лексический поиск; provider latency в него не входит.
