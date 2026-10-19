# Lab 5: ablation и последние решения

## Воспроизведение

```bash
MODEL_PROVIDER=deterministic python -m ml.experiments.run_ablation
python tests/evals/run_evals.py --output artifacts/evals/lab5-final-results.json
```

Прогон отключает улучшения **по одному** на одних и тех же frozen review-кейсах: phrase aliases, русский стемминг, опору на source quote и contradiction guard. Отдельный контрольный вариант отключает весь semantic preprocessing и оставляет сырое лексическое пересечение. В Lab5 добавлена поддержка варианта написания «кэше» с буквой `э`, подтверждённая кейсом `REV-001`. JSON содержит предсказание каждого варианта по каждому кейсу и лежит в `artifacts/experiments/lab5-ablation-results.json`.

Фактический результат: полный набор semantic rules дал **92,86% (39/42)**. Без phrase aliases — 88,10% (−4,76 п.п.), без стемминга — 90,48% (−2,38 п.п.), без source precision — 90,48% (−2,38 п.п.), без contradiction guard — 88,10% (−4,76 п.п.), сырой lexical overlap — 71,43% (−21,43 п.п.). По сравнению с Lab3/Lab4 итоговый review agreement вырос с 90,48% до 92,86% (+2,38 п.п.).

Отдельное provider-сравнение не выдумывается заново: фактический Gemini-прогон `lab4-provider-results.json` показал prompt B 100% против A 95% на 20 кейсах. Цена — 6380 против 3843 токенов (+66%). В релизе оставлены prompt B и полный набор semantic rules: они дали измеримый прирост, тогда как простое лексическое пересечение хуже принимает ответы своими словами.

Что не сработало: простое снижение порога совпадения повышало риск принять неполные ответы, поэтому его не включили. Три кейса, где ответ дословно совпадает с `reference_answer`, но dataset ожидает `partially_correct`, оставлены как известная проблема разметки, а не «исправлены» под метрику.

Ограничение: Gemini A/B — один прогон малой выборки на `gemini-3.5-flash-lite`; его нельзя выдавать за полный eval или за `gemini-3.8-flash`. Финальный полный quality gate остаётся воспроизводимым deterministic-прогоном.
