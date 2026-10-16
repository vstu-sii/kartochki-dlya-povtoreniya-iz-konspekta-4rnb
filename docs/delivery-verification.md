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
