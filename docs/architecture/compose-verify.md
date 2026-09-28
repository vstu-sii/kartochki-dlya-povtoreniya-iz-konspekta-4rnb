# Проверка compose-скелета — лабораторная 2

**Дата:** 2026-09-28  
**Файл:** `compose.dev.yml`

## Что проверяем

Compose Lab 2 поднимает заглушки сервисов с health checks. Docker Desktop в текущей машине сдачи не установлен, поэтому проверка выполнена в два слоя.

## 1. Статический разбор compose

Проверено автотестом `tests/test_lab2_all_artifacts.py::test_compose_has_services_networks_volumes_and_healthchecks`:

| Требование | Статус |
|---|---|
| сервисы frontend, telegram-adapter, app-api, data-service, ai-service, postgres | есть |
| networks `edge` + `internal` (`internal: true`) | есть |
| volume `postgres-data` | есть |
| healthcheck у сервисов | ≥5 |
| schema монтируется в postgres init | есть |

## 2. Health-заглушки без Docker

Запущены процессы `backend/app.py` и `ml/app.py` на локальных портах; все ответили `200` на `/health`:

| Сервис | URL | Ответ |
|---|---|---|
| telegram-adapter | `http://127.0.0.1:18001/health` | `{"service":"telegram-adapter","status":"ok","implementation":"lab2-stub"}` |
| app-api | `http://127.0.0.1:18002/health` | `{"service":"app-api","status":"ok","implementation":"lab2-stub"}` |
| data-service | `http://127.0.0.1:18003/health` | `{"service":"data-service","status":"ok","implementation":"lab2-stub"}` |
| ai-service | `http://127.0.0.1:18004/health` | `{"service":"ai-service","status":"ok","implementation":"lab2-stub",...}` |

## 3. Команда на машине с Docker

Когда Docker Desktop доступен у члена команды Delivery:

```bash
docker compose -f compose.dev.yml config
docker compose -f compose.dev.yml up --build -d
docker compose -f compose.dev.yml ps
```

Ожидание: все сервисы `healthy`, UI на `http://localhost:8080`.

**Статус Lab 2:** скелет проверен статически и через health-заглушки; контракт compose готов к подъёму на машине с Docker в лабе 3.
