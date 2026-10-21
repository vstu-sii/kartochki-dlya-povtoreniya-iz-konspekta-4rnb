# Финальные метрики AI на релизе `v0.5.1`

| Этап | Набор | Schema | Grounding | Review agreement | Latency | Стоимость/токены |
|---|---:|---:|---:|---:|---|---|
| Lab 3 baseline | 95 model cases | 100% | 100% | 90,48% | local p50 1 мс, p95 3 мс | 23 674 in / 13 275 out |
| Lab 4 Gemini prompt A | 20 cases | по schema | grounded grader | 95% | provider latency сохранена по кейсам | 3 843 tokens |
| Lab 4/5 Gemini prompt B | 20 cases | по schema | grounded grader | 100% | provider p50 6227,85 мс, p95 6569,36 мс | 6 380 tokens |
| Lab 5 deterministic release `v0.5.1` | 95 model + 37 application cases | 100% | 100% | **92,86%** | local p50 3 мс, p95 3 мс | 15 732 in / 14 471 out |

Источник истины — JSON-артефакты, документ только объясняет их. Локальные миллисекунды измеряют код fallback и не заменяют latency Gemini. Для B p50 рассчитан как медиана, p95 — методом nearest rank по 20 вызовам этого варианта. Выбран B из-за +5 п.п.; цена выбора — +2537 токенов (+66%). На использованном бесплатном Gemini tier денежное списание равно $0, но токены остаются ресурсом квоты. Для продукта это означает более надёжную смысловую оценку ценой большей квоты и примерно 6,57 с p95, поэтому fallback и бюджетный tier сохранены.

Поэлементная ablation подтверждает вклад каждого механизма: aliases −4,76 п.п. при отключении, stemming −2,38 п.п., source precision −2,38 п.п., contradiction guard −4,76 п.п. Полный результат и строки по кейсам: `artifacts/experiments/lab5-ablation-results.json`.

## Дополнительная приёмка критериев Lab 1

Пакет для таблицы Quality описан в `docs/quality/lab1-ai-evidence.md`; сырые данные находятся в `artifacts/evals/lab1-ai-quality-evidence.json`. В нём подготовлены 20 разборов с ответами, эталонами и результатами системы. Ручные критерии, проверка тезисов/формул по PDF, полная стоимость сценария и end-to-end latency не объявляются пройденными до совместного замера с Quality и Delivery.
