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

17 октября 2026 года выполнен настоящий прогон через официальный Google Gemini API. Взяты 20 фиксированных примеров golden dataset: первые 10 сценариев генерации карточек и первые 10 сценариев проверки ответа. Каждый пример выполнен с вариантами A и B, всего 40 LLM-вызовов. Ключ в репозиторий и артефакт не записывался.

Для прогона использована `gemini-3.5-flash-lite`. Настроенная в прототипе `gemini-3.8-flash` в момент запуска вернула `RESOURCE_EXHAUSTED`: бесплатный дневной лимит 20 запросов был исчерпан. Поэтому вывод ниже относится именно к `gemini-3.5-flash-lite`; провайдер при этом тот же — официальный Google Gemini API.

Результат:

- prompt A (`v1`): 19 из 20, agreement **95%**, 3 843 токена;
- prompt B (`v2`): 20 из 20, agreement **100%**, 6 380 токенов;
- изменение качества: **+5 п.п.**;
- цена выбора B: **+2 537 токенов**, или примерно **+66%** на этой выборке.

Выбран **prompt B (`v2`)**: он устранил единственную ошибку варианта A (`REV-009`, неполный ответ о потоках и процессах). Цена решения — больший расход токенов; для интерактивного MVP команда принимает эту цену ради более точной обратной связи. Перед production-оптимизацией решение следует перепроверить на полном наборе и нескольких повторах.

Без ключа выполняется только контрактная проверка:

```bash
python -m ml.experiments.run_ab --mode contract
```

Она подтверждает, что оба промпта рендерятся на одном dataset, но намеренно ставит `provider_called=false` и `quality_measured=false`.

## Артефакты

- `lab4-algorithm-results.json` — 40 строк фактического локального сравнения алгоритмов;
- `lab4-contract-results.json` — provider-free проверка шаблонов;
- `lab4-provider-results.json` — фактический Gemini A/B: ответы, latency, provider usage и решение по каждому кейсу.

Решение: prompt v2 выбран для Gemini, алгоритм B оставлен как deterministic fallback.
