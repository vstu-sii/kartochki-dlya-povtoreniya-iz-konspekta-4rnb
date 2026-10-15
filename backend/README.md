# Backend

Health-only HTTP-сервис для трёх контейнеров compose: `telegram-adapter`, `app-api`, `data-service`. Имя задаётся `SERVICE_NAME`; `GET /health` используется health check.

Назначение в лабораторной 2 — проверить границы C4, сети и параллельную работу ролей. Handlers прикладного API и интеграция с Telegram добавляются в лабораторной 3.
