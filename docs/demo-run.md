# Протокол прогона AI-кейсов Demo Day

## Финальная репетиция на выбранном теге

- Дата: 30.10.2026.
- Публичный URL: `https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com`.
- Ответ `/health`: `status=ok`, версия `lab5`, SHA `a60eee706ad17238c11e0c79f53f026fd68bdf81`.
- Выбранный командой тег, указывающий на этот SHA: `v0.5.10-demo-candidate`.
- Модель фактических ответов: `gemini-3.5-flash-lite`.
- Повторы: 5 кейсов × 3 = 15 публичных попыток; дополнительно две setup-генерации для настоящих сессий.
- Результат: **15/15** ответов прошли заранее записанные проверки; у всех пяти кейсов стабильный продуктовый исход; `fallback_used=false` во всех публичных попытках.
- Задержка клиента по 15 успешным попыткам: median **1,777 с**, p95/max **2,909 с**.
- Plan B: injected timeout — **PASS**, deterministic fallback вернул 5 карточек и trace.

Полные запросы, ответы, trace/review ID, usage и задержки: `artifacts/demo/lab6-ai-demo-v0.5.10.json`. Статический бэкап: `docs/demo/cache/ai-demo-backup-v0.5.10.json`.

## Команды воспроизведения

Из корня репозитория:

```powershell
py -3 -m tests.evals.run_lab6_demo `
  --base-url https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com `
  --repeats 3 `
  --pause-seconds 2 `
  --output artifacts/demo/lab6-ai-demo-v0.5.10.json `
  --backup-output docs/demo/cache/ai-demo-backup-v0.5.10.json
```

Если ответы уже записаны и изменился только код проверки результата:

```powershell
py -3 -m tests.evals.run_lab6_demo `
  --revalidate-existing artifacts/demo/lab6-ai-demo-v0.5.10.json `
  --output artifacts/demo/lab6-ai-demo-v0.5.10.json
```

Вторая команда не вызывает Gemini: она повторно проверяет сохранённые raw HTTP responses. Этот режим использован после исправления валидатора, который первоначально искал правильное исправление только в `feedback`, хотя контракт также разрешает `missing_points`.

Ноутбук `notebooks/lab6_demo_cases.ipynb` показывает сводку, таблицу пяти кейсов и сохранённый бэкап; сам источник логики — versioned runner `tests/evals/run_lab6_demo.py`.

## Интерпретация

Функциональная часть выбранных демо-кейсов стабильна: карточки имеют ровно пять элементов и grounded-цитаты; три типа review стабильно различаются; ошибочная ссылка на жёсткий диск исправляется. На финальной репетиции все 15 попыток уложились в 2,909 с, но это не отменяет риск внешнего провайдера: предыдущий smoke уже фиксировал timeout. Поэтому для выступления сохраняется согласованный командой Plan B с порогом переключения **30 секунд**.

## История до выбора финального тега

29.10.2026 production `/health` изменился на нетегированный SHA `a60eee706ad17238c11e0c79f53f026fd68bdf81`. После исправления runner выполнен отдельный smoke с одним повтором каждого кейса:

- подготовка двух настоящих сессий и выбор принадлежащих им карточек — PASS;
- полный ответ — `correct`, неполный — `partially_correct`, ошибка про жёсткий диск — `incorrect`;
- 4/5 кейсов прошли через `gemini-3.5-flash-lite` без fallback;
- AI-DEMO-01 после 61,636 с вернулся через `deterministic-grounded-v2`, `fallback_reason=gemini_timeout`;
- по четырём успешным Gemini-вызовам median 26,366 с, p95/max 29,184 с.

Сырой результат: `artifacts/demo/lab6-ai-smoke-a60eee7.json`. Этот smoke подтвердил работоспособность Plan B и необходимость согласованного порога 30 секунд. После него команда назначила тег `v0.5.10-demo-candidate` на тот же production SHA, а AI выполнил новый полный прогон 5×3, описанный выше.

## Граница доказательства

Финальный прогон подтверждает публичный API и AI-кейсы именно для SHA выбранного тега `v0.5.10-demo-candidate`. Локальная injected-проверка подтверждает backend-деградацию, но не имитирует реальный отказ внешнего провайдера в production и не отправляет тестовый PDF в настоящий пользовательский Telegram-чат. Пользовательское поведение проверено по Delivery-коду этого же SHA: при `fallback_used=true` Telegram сообщает, что карточки созданы «резервным алгоритмом», то есть деградация не выдаётся за ответ Gemini.
