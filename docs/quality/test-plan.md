# Тест-план лабораторной 3

## Цели

Проверить четыре свойства MVP: договорённости API не расходятся, данные не теряются, AI-выход подтверждён источником, недоверенный PDF не получает прав внутри системы.

## Уровни

| Уровень | Что проверяем | Инструмент / двойник | Когда |
|---|---|---|---|
| Unit | PDF limits, token budget, normalization, schema validator, grounding, duplicate detector, cost calculation | `unittest`/`pytest`, без сети | каждый PR |
| Contract | OpenAPI request/response, коды ошибок, idempotency, совместимость app ↔ AI | OpenAPI validator + generated fixtures | каждый PR |
| Database | constraints, FK/cascade, миграция с нуля, TTL job, изоляция user_id | временный PostgreSQL | каждый PR |
| Integration | Telegram Adapter → Application API → mock AI/Data | compose, provider mock | каждый PR |
| AI eval mini | 6 фиксированных модельных кейсов: 4 generation и 2 review | `tests/evals/run_evals.py --mini`, замороженные model/prompt | каждый PR |
| AI eval full | все модельные кейсы `generate_card` и `review_answer` из 128 строк dataset v2 | тот же runner; одна детерминированная реализация baseline | nightly, вручную и перед релизом |
| API/DB E2E | `reject_input`, `validate_model_output`, `rate_card`, `resume_session`, `complete_session` | compose + HTTP assertions | Delivery CI; расширение security-набора — лаба 4 |
| Security | prompt injection, oversized input, output escaping, secret/log leak, IDOR | pytest + attack fixtures; модельный runner не подменяет эти проверки | каждый PR (дешёвые), полный в лабе 4 |
| Performance | p50/p95 generation/review, concurrency, timeout/fallback | k6/Locust | перед релизом |
| Manual UC | пять сценариев без подсказок | человек не из команды | конец спринта |

## Матрица UC

| UC | Unit | Contract | Integration | Eval | Security | Manual |
|---|---:|---:|---:|---:|---:|---:|
| UC-01 генерация | да | да | да | GEN-* | SAFE-002…006 | да |
| UC-02 ответ | да | да | да | REV-* | SAFE-001/003 | да |
| UC-03 оценка | да | в лабе 3 | да | UX-* после MVP | IDOR | да |
| UC-04 прогресс | да | в лабе 3 | да | STATE-* после MVP | IDOR/TTL | да |
| UC-05 отклонение | да | да | да | SAFE-* | да | да |

## Метрики и пороги после baseline

- schema pass rate после максимум одного repair: 100%;
- grounded-card rate: ≥95%;
- review agreement rate: ≥85% для merge-gate mini-набора; полный baseline фиксируется без сокрытия провалов;
- safety guard rate публикуется только после реального вызова API/guard, а не присваивается runner-ом;
- p95 generation ≤60 секунд, p95 review ≤7 секунд;
- стоимость полной сессии ≤$0.04;
- 0 утечек секретов/чужих сессий в security tests.

Порог качества подтверждается baseline, а не объявляется фактом заранее. Для offline-метрик используются соответствующие поднаборы: `GEN` — schema/grounding, `REV` — согласие с эталонным verdict. `SAFE`, `UX` и `STATE` не считаются модельными ответами: runner помечает их `executed=false` и передаёт проверку API/БД. Пользовательская полезность подтверждается telemetry реальных оценок, а не UX-фикстурами.

## CI с лабораторной 3

На PR запускается mini-eval с отдельными порогами `schema=1.00`, `grounding=0.95`, `review=0.85`: плохую метрику нельзя скрыть средним баллом. По расписанию и вручную запускается полный eval. Результаты и JSONL-трейсы сохраняются как CI-артефакты с `model`, `prompt_version`, `dataset_version`, latency и токенами.

Полный dataset содержит 128 строк. Текущий model runner реально выполняет 95 модельных случаев и явно пропускает 33 API/DB-сценария с причиной `requires_api_or_database_e2e`. Текущий baseline детерминированный и выполняется один раз; три стохастических прогона, сравнение primary/fallback и денежная стоимость появятся после подключения внешнего провайдера и не выдаются за уже выполненные.

## Тестовые данные

Используются синтетические фрагменты без персональных данных. Реальные PDF добавляются только с правом использования и не коммитятся; в dataset попадают короткие разрешённые фрагменты и происхождение. Эталон создаёт/проверяет человек, не та же модель.

## Выход из тестирования

Все автоматические проверки зелёные; нет открытых critical/high угроз; ручные UC прожиты; невыполненный внешний прогон явно обозначен и не маскируется моками.
