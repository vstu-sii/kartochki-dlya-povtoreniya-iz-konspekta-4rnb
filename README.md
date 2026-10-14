# Lab 3 — Quality & Safety

Ветка содержит воспроизводимый eval baseline для сервиса «Карточки для повторения из конспекта».

## Как проверить

```bash
python tests/evals/run_evals.py --mini --min-schema 1 --min-grounding 0.95 --min-review 0.85 --output artifacts/evals/mini-results.json
python tests/evals/run_evals.py --output artifacts/evals/baseline-results.json
```

Mini-набор является merge-gate. Полный прогон выполняется по расписанию и вручную workflow `Lab3 evals`. Результаты и трейсы сохраняются в `artifacts/evals/` и как CI-артефакты.

## Что измеряется

- соответствие структуры генерации контракту;
- привязка карточек к переданному контексту и странице;
- согласие разбора ответа с эталонным verdict;
- latency и оценка числа входных/выходных токенов.

Операции API и БД (`SAFE`, `UX`, `STATE`) не объявляются успешно выполненными без вызова соответствующего кода. В отчёте они имеют `executed=false` и проверяются интеграционными тестами Delivery.

## Связанные ветки

- Product: https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/tree/lab3-product-prototype
- AI: https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/tree/lab3-ai-prototype
- Delivery и E2E: https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/tree/lab3-delivery-prototype
