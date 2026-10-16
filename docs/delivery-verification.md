# Проверка Delivery лабораторной 4

## Что проверяется автоматически

Workflow `Lab4 delivery staging and observability`:

1. валидирует production и staging Compose;
2. проверяет правила Prometheus и моделирует срабатывание двух token-budget алертов;
3. поднимает staging из `compose.yml` и `compose.staging.yml`;
4. проверяет UI, trace viewer, Prometheus, Grafana и загрузку alert rules;
5. при ошибке публикует логи и всегда удаляет тестовые volumes.

Staging не имеет отдельной архитектуры: override меняет только окружение, лимиты и внешние порты. Поэтому проверяется тот же набор образов и сервисов, который используется в production.

## Что настраивается владельцем репозитория один раз

- GitHub Actions secret `RENDER_DEPLOY_HOOK_URL`;
- GitHub Actions variable `PRODUCTION_HEALTH_URL` со значением публичного `/health`;
- Render secrets `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `DATABASE_URL`;
- production-пароль Grafana.

Эти значения намеренно отсутствуют в Git. Workflow деплоя останавливается до вызова Render, если deploy hook или health URL не заданы. Факт реального production deploy подтверждается только успешным run `Test, build and deploy production` после merge в `main`.

## Ручная демонстрация

```bash
docker compose -f compose.yml -f compose.staging.yml up -d --build --wait
```

После запуска: UI — `http://localhost:8081`, traces — `http://localhost:3010`, Prometheus — `http://localhost:9091`, Grafana — `http://localhost:3002`.

## Репетиция отката

Workflow `Lab4 rollback rehearsal` выполняет реальный staging-drill без воздействия на production: поднимает текущий commit, переключает Compose-контур на предыдущий зелёный commit `e62bf85411de4208b4a6c7db384d11f730019472`, проверяет `/health`, затем восстанавливает текущий commit и повторяет health check. Три ответа и обе ревизии сохраняются в артефакте `lab4-rollback-rehearsal`.

### Фактический прогон 16.10.2026

Репетиция действительно выполнена в GitHub Actions, а не только описана скриптом: [workflow run №38925580068](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/38925580068) завершился со статусом `success`.

| Этап | Ревизия | Результат |
| --- | --- | --- |
| Исходная staging-версия | `4d0bcf913aee155c2e099f117c3589a836a5eedd` | Compose поднялся, `/health` успешно ответил |
| Откат | `e62bf85411de4208b4a6c7db384d11f730019472` | Предыдущая версия поднялась, `/health` успешно ответил |
| Возврат после репетиции | `4d0bcf913aee155c2e099f117c3589a836a5eedd` | Текущая версия восстановлена, `/health` успешно ответил |

Workflow сохранил проверяемый артефакт `lab4-rollback-rehearsal` (artifact id `12056876809`) с обеими ревизиями и тремя ответами health endpoint. Диагностический шаг не запускался, потому что ошибок не было.

После попадания `deploy.yml` в `main` production rollback запускается одной командой `scripts/rollback.sh <verified-sha>`. Production-drill выполняется только после появления минимум двух успешных production deploy, чтобы не выдавать staging-проверку за откат реальных пользовательских данных.
