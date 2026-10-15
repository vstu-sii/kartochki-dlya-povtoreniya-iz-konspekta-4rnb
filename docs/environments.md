# Environments: local, staging, production

Staging and production use the same images and `compose.yml`. Staging is an override, not a separate architecture:

```bash
docker compose -f compose.yml -f compose.staging.yml up -d --build --wait
```

| Параметр | Local/prod-like | Staging | Причина отличия |
|---|---|---|---|
| UI port | 8080 | 8081 | Можно поднять рядом |
| Grafana | 3001 | 3002 | Можно поднять рядом |
| Provider | из `.env` | deterministic по умолчанию | CI не получает внешний ключ |
| Request/token limits | 50 / 120k | 20 / 40k | Быстро проверять деградацию |
| Данные | отдельный volume | отдельный project volume | Не смешивать пользовательские данные |

Production secrets (`GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, deploy hook, Grafana password) задаются на Render/GitHub и не коммитятся. Перед запуском проверяются обе конфигурации командой `docker compose ... config --quiet`.
