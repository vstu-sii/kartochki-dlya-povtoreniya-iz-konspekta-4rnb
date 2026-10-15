# Lab 3 — Quality & Safety

Ветка содержит воспроизводимый eval baseline для сервиса «Карточки для повторения из конспекта».

## Как проверить

```bash
python tests/evals/run_evals.py --mini --min-schema 1 --min-grounding 0.95 --min-review 0.85 --min-safety 1 --output artifacts/evals/mini-results.json
python tests/evals/run_evals.py --output artifacts/evals/baseline-results.json
```

Mini-набор является merge-gate. Полный прогон запускается второй командой выше. Расписание workflow `Lab3 evals` начнёт работать после попадания workflow в default branch. Результаты и трейсы сохраняются в `artifacts/evals/` и как CI-артефакты.

## Что измеряется

- соответствие структуры генерации контракту;
- привязка карточек к переданному контексту и странице;
- согласие разбора ответа с эталонным verdict;
- latency и оценка числа входных/выходных токенов.

Операции API и БД (`SAFE`, `UX`, `STATE`) не объявляются успешно выполненными без вызова соответствующего кода. В отчёте они имеют `executed=false` и проверяются интеграционными тестами Delivery.

Полный результат разделён на два доказательства: 95 модельных кейсов в `baseline-results.json` и 33/33 прикладных кейса в `application-results.json`. Review agreement полного модельного прогона — 90,48% при пороге 85%.

## Связанные ветки

- Product: https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/tree/lab3-product-prototype
- AI: https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/tree/lab3-ai-prototype
- Delivery и E2E: https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/tree/lab3-delivery-prototype

Mini содержит ровно 8 фиксированных кейсов: 4 generation, 2 review, 2 safety. Safety проверяет настоящую guard-функцию; HTTP-проверки находятся в `tests/test_http_guards.py`. Для HTTP-тестов установите `pip install -r backend/requirements.txt`, затем `python -m unittest discover -s tests`.

Технические результаты и ограничения: `docs/quality/verification-2026-10-15.md`. Генерация cards-v2.0 возвращает от 1 до requested_card_count независимых grounded-карточек; review-v2.0 использует семантическую проверку primary-модели и воспроизводимый fallback.
