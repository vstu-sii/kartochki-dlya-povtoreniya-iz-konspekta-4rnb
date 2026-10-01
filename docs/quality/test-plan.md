# Тест-план лабораторной 2

## Цели

Проверить четыре свойства MVP: договорённости API не расходятся, данные не теряются, AI-выход подтверждён источником, недоверенный PDF не получает прав внутри системы.

## Уровни

| Уровень | Что проверяем | Инструмент / двойник | Когда |
|---|---|---|---|
| Unit | PDF limits, token budget, normalization, schema validator, grounding, duplicate detector, cost calculation | `unittest`/`pytest`, без сети | каждый PR |
| Contract | OpenAPI request/response, коды ошибок, idempotency, совместимость app ↔ AI | OpenAPI validator + generated fixtures | каждый PR |
| Database | constraints, FK/cascade, миграция с нуля, TTL job, изоляция user_id | временный PostgreSQL | каждый PR |
| Integration | Telegram Adapter → Application API → mock AI/Data | compose, provider mock | каждый PR |
| AI eval mini | 8 фиксированных кейсов: 4 generation, 2 review, 2 safety | runner поверх JSONL, замороженные model/prompt | каждый PR после лабы 3 |
| AI eval full | все 120+ кейсов, метрика по уникальным кейсам и три прогона для проверки вариативности, разрез primary/fallback | выбранный eval tool | nightly и перед релизом |
| Security | prompt injection, oversized input, output escaping, secret/log leak, IDOR | pytest + attack fixtures | каждый PR (дешёвые), полный в лабе 4 |
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
- полезность карточек: ≥80%;
- доля противоречащих эталону review: ≤5%;
- p95 generation ≤60 секунд, p95 review ≤7 секунд;
- стоимость полной сессии ≤$0.04;
- 0 утечек секретов/чужих сессий в security tests.

Порог качества подтверждается baseline, а не объявляется фактом заранее. До реального запуска значения являются критериями приёмки. Для offline-метрик используются соответствующие поднаборы: `GEN` — schema/grounding, `REV` — непротиворечивость разбора, `SAFE` — защитные отказы. Пользовательская полезность подтверждается telemetry реальных оценок, а не десятью UX-фикстурами.

## CI с лабораторной 3

На PR: синтаксис, unit, contract, миграция, compose build, mini-eval. Полный eval не запускается на каждый коммит из-за стоимости; он идёт nightly и перед релизом. Результат сохраняется как JSON/JUnit с `model`, `prompt_version`, `dataset_version`, latency и cost.

## Тестовые данные

Используются синтетические фрагменты без персональных данных. Реальные PDF добавляются только с правом использования и не коммитятся; в dataset попадают короткие разрешённые фрагменты и происхождение. Эталон создаёт/проверяет человек, не та же модель.

## Выход из тестирования

Все автоматические проверки зелёные; нет открытых critical/high угроз; ручные UC прожиты; невыполненный внешний прогон явно обозначен и не маскируется моками.
