# Эксперименты AI Lab4

## 1. Историческое A/B алгоритмов проверки

Команда:

```bash
python -m ml.experiments.run_ab --mode algorithm --min-b-agreement .85 --fail-on-regression
```

На 40 одинаковых review-кейсах алгоритм A (`lexical-overlap-v1`) получил 82,5%, алгоритм B (`normalized-semantic-rules-v2`) — 90,0%, разница +7,5 п.п. Это **сравнение алгоритмов**, а не доказательство улучшения текста промпта. Оно сохраняется как воспроизводимый regression gate без внешнего API.

## 2. Prompt-only A/B

Сценарий `--mode provider` меняет только prompt v1/v2. Dataset, модель, JSON Schema, `thinkingLevel=low`, `maxOutputTokens=6000`, обработка ответа и grader одинаковы. Генерация карточек и проверка ответа оцениваются раздельно в строках результата; сохраняются ответ каждого кейса, latency и provider usage.

```bash
GEMINI_API_KEY=... python -m ml.experiments.run_ab --mode provider \
  --model gemini-3.5-flash-lite --case-limit 20 --repeats 1 \
  --output artifacts/experiments/lab4-provider-results.json
```

17.10.2026 выполнен настоящий прогон через официальный Google Gemini API: 20 фиксированных кейсов, по вариантам A и B, всего 40 вызовов. Фактическая модель — `gemini-3.5-flash-lite`; настроенная `gemini-3.8-flash` вернула `RESOURCE_EXHAUSTED`, поэтому вывод нельзя переносить на неё.

- prompt A: 95%, 3 843 токена;
- prompt B: 100%, 6 380 токенов;
- прирост: +5 п.п.; цена: +2 537 токенов (+66%).

Выбран prompt B: он устранил ошибку `REV-009`. Артефакт содержит ответы, latency и provider usage каждого вызова; ключ не сохранялся.

Без ключа выполняется только контрактная проверка:

```bash
python -m ml.experiments.run_ab --mode contract
```

Она подтверждает, что оба промпта рендерятся на одном dataset, но намеренно ставит `provider_called=false` и `quality_measured=false`.

## Артефакты

- `lab4-algorithm-results.json` — 40 строк фактического локального сравнения алгоритмов;
- `lab4-contract-results.json` — provider-free проверка шаблонов;
- `lab4-provider-results.json` — фактический Gemini A/B.

Решение: prompt v2 выбран для Gemini, алгоритм B оставлен deterministic fallback.
