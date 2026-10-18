# Финальные метрики AI на release candidate Lab 5

| Этап | Набор | Schema | Grounding | Review agreement | Latency | Стоимость/токены |
|---|---:|---:|---:|---:|---|---|
| Lab 3 baseline | 95 model cases | 100% | 100% | 90,48% | local p50 1 мс, p95 3 мс | 23 674 in / 13 275 out |
| Lab 4 Gemini prompt A | 20 cases | по schema | grounded grader | 95% | provider latency сохранена по кейсам | 3 843 tokens |
| Lab 4/5 Gemini prompt B | 20 cases | по schema | grounded grader | 100% | provider latency сохранена по кейсам | 6 380 tokens |
| Lab 5 deterministic release candidate | 95 model + 33 application cases | 100% | 100% | 90,48% | local p50 1 мс, p95 2 мс | 15 732 in / 14 851 out |

Источник истины — JSON-артефакты, документ только объясняет их. Локальные миллисекунды измеряют код fallback и не заменяют latency Gemini. Выбран B из-за +5 п.п.; цена выбора — +2537 токенов. Для продукта это означает более надёжную смысловую оценку, но более дорогую сессию, поэтому fallback и бюджетный tier сохранены.
