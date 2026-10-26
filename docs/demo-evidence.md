# Доказательства для Demo Day

## Tagged release

- тег: `v0.5.1`, commit `e0ca9b9`;
- [воспроизводимая сборка — success](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/39221429842);
- [полный quality gate — success](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/39221429651).

Снимок страницы успешного прогона сохранён без редактирования: [`docs/evidence/lab5/v0.5.1-quality-gate.png`](evidence/lab5/v0.5.1-quality-gate.png). На нём видны тег, commit, статус Success, длительность и CI-артефакт.

## Наблюдаемость

Конфигурация dashboard хранится как код: `monitoring/grafana/dashboards/flashcards-overview.json`. Staging CI поднимает тот же Compose-контур, проверяет UI, trace dashboard, Prometheus, Grafana и alert rules, а затем подтверждает отсутствие `pending`/`firing` алертов. JSON этой проверки сохраняется в CI-артефакте `staging-alert-status`. Метрики production-периода сохранены в `artifacts/reliability/prod-window.json`; трассировка по умолчанию редактирует содержимое prompt/response.

Последнее окно 27.10.2026: 30/30 успешных проб, uptime 100%, p50 586,24 мс, p95 2231,14 мс. Затем Render успешно развернул commit `af194ff` из `lab5-delivery-testing`; отдельный `prod-version-check.json` подтвердил HTTP 200, `version: lab5` и `version_match_percent: 100`.

## Что показать преподавателю

1. Открыть первый CI-run и показать зелёный job сборки по тегу `v0.5.1`.
2. Открыть второй CI-run и показать зелёные model, application, security и retrieval gates.
3. Поднять staging одной командой и открыть Grafana `http://localhost:3002`; показать request rate, p95, 5xx, budget decisions и алерт.
4. Показать `artifacts/reliability/prod-window.json`: 30/30, uptime 100%, p50 586,24 мс, p95 2231,14 мс.
5. Показать `prod-version-check.json`: release smoke-check завершился кодом 0 и подтвердил `version_match_percent: 100`.

Снимок локальной Grafana не коммитится как «факт», пока dashboard реально не открыт на машине с Docker. Ссылки CI и JSON являются проверяемыми доказательствами; скриншот преподаватель может получить на приёмке из живого контура.
