# Retrieval evaluation Lab4

Команда:

```bash
python -m ml.experiments.run_retrieval_eval --min-hit-at-1 .90 --min-recall-at-3 1.0
```

Один прогон сохраняет три разных свидетельства:

1. `curated_query` — отдельное качество поиска по заданному запросу;
2. `production_query_builder` — тот же способ формирования запроса из первых 200 символов каждой страницы, который использует `BaselineModel`;
3. `end_to_end` — путь pages → production query → top-3 → deterministic cards.

На десяти синтетических сценариях curated и production-query получили hit@1=100%, recall@3=100%, MRR=1,0. Это проверка небольшого корпуса и не оценка качества всего продукта.

В отдельном пятистраничном coverage probe top-3 сохранил страницы 1–3 и отбросил 4–5. Следовательно, ограничение в три фрагмента действительно может потерять важную часть длинного документа. До перехода к chunking/coverage-aware retrieval UI и документация не должны обещать полноту по всему PDF.

Latency в JSON — локальное время deterministic lookup, не production SLA.
