# Lab 5: ablation и последние решения

## Воспроизведение

```bash
MODEL_PROVIDER=deterministic python -m ml.experiments.run_ablation
python tests/evals/run_evals.py --output artifacts/evals/lab5-final-results.json
```

Первый прогон отключает нормализацию и семантические правила только в контрольном варианте и сравнивает его с текущим fallback на тех же frozen review-кейсах. JSON с каждой строкой лежит в `artifacts/experiments/lab5-ablation-results.json`.

Отдельное provider-сравнение не выдумывается заново: фактический Gemini-прогон `lab4-provider-results.json` показал prompt B 100% против A 95% на 20 кейсах. Цена — 6380 против 3843 токенов (+66%). В релизе оставлены prompt B и полный набор semantic rules: они дали измеримый прирост, тогда как простое лексическое пересечение хуже принимает ответы своими словами.

Ограничение: Gemini A/B — один прогон малой выборки на `gemini-3.5-flash-lite`; его нельзя выдавать за полный eval или за `gemini-3.8-flash`. Финальный полный quality gate остаётся воспроизводимым deterministic-прогоном.
