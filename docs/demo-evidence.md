# Доказательства для Demo Day

## Tagged release

- тег: `v0.5.1`, commit `e0ca9b9`;
- [воспроизводимая сборка — success](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/39221429842);
- [полный quality gate — success](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/39221429651).

## Наблюдаемость

Конфигурация dashboard хранится как код: `monitoring/grafana/dashboards/flashcards-overview.json`. Staging CI поднимает тот же Compose-контур и проверяет UI, trace dashboard, Prometheus, Grafana и alert rules. Метрики production-периода сохранены в `artifacts/reliability/prod-window.json`; трассировка по умолчанию редактирует содержимое prompt/response.

## Что показать преподавателю

1. Открыть первый CI-run и показать зелёный job сборки по тегу `v0.5.1`.
2. Открыть второй CI-run и показать зелёные model, application, security и retrieval gates.
3. Поднять staging одной командой и открыть Grafana `http://localhost:3002`; показать request rate, p95, 5xx, budget decisions и алерт.
4. Показать `artifacts/reliability/prod-window.json`: 30/30, uptime 100%, p50 793,83 мс, p95 2437,77 мс.

Снимок локальной Grafana не коммитится как «факт», пока dashboard реально не открыт на машине с Docker. Ссылки CI и JSON являются проверяемыми доказательствами; скриншот преподаватель может получить на приёмке из живого контура.
