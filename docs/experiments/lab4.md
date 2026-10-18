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
  --model gemini-3.8-flash --repeats 3 --fail-on-regression
```

Настоящий provider prompt A/B в этой локальной доработке **не выполнен**, потому что ключ и разрешение на платные вызовы не предоставлены. Поэтому выбора prompt v2 «по цифрам LLM» пока нет. Файл `artifacts/experiments/lab4-provider-results.json` появится только после разрешённого запуска.

Без ключа выполняется только контрактная проверка:

```bash
python -m ml.experiments.run_ab --mode contract
```

Она подтверждает, что оба промпта рендерятся на одном dataset, но намеренно ставит `provider_called=false` и `quality_measured=false`.

## Артефакты

- `lab4-algorithm-results.json` — 40 строк фактического локального сравнения алгоритмов;
- `lab4-contract-results.json` — provider-free проверка шаблонов;
- `lab4-provider-results.json` — создаётся только реальным разрешённым запуском.

Решение на текущих доказательствах: алгоритм B оставлен как deterministic fallback. Решение о превосходстве prompt v2 над v1 отложено до provider-прогона.
