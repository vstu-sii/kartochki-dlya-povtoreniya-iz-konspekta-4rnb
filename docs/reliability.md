# Надёжность публичного прототипа

```powershell
python tests/reliability/measure_prod.py `
  --url https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com/health `
  --samples 30 --interval 5 --min-uptime 99 `
  --expected-version lab5
```

`artifacts/reliability/prod-window.json` хранит каждую пробу, границы и фактическую
длительность периода, uptime, p50, p95 и версию ответа. Файл атомарно обновляется
после каждой пробы. Команда завершается с ненулевым кодом, если uptime ниже порога
или хотя бы один успешный ответ пришёл не от ожидаемой версии. Поэтому один и тот же
скрипт является и измерителем, и release smoke-check.

Фактическое контрольное окно 27.10.2026 по местному времени
(`2026-10-26T22:33:51Z`—`22:36:39Z`): 30/30 успешных проб,
**uptime 100%**, p50 **586,24 мс**, p95 **2231,14 мс**. Все сырые пробы
сохранены. Повышенный p95 остаётся ограничением бесплатного Render-инстанса.

Проверка версии отдельно сохранена в
`artifacts/reliability/prod-version-check.json`. На момент проверки публичный
Render отвечал `lab4`, хотя ветка Delivery уже содержит `APP_VERSION=lab5`.
Проверка ожидаемо завершилась кодом 1. Это честно фиксирует deployment drift:
доступность подтверждена, но Lab 5 ещё нужно развернуть в Render.

Для недельного наблюдения используется та же команда с `--samples 2016
--interval 300`. Короткое окно выше не выдаётся за недельный SLA; историю за
длительный период на приёмке дополняют метрики Render/Grafana.

После запуска staging CI выполняет
`tests/reliability/check_prometheus_alerts.py`. Проверка падает при любом
`pending`/`firing` алерте и сохраняет `staging-alert-status` как CI-артефакт.
Поведение самих token-budget алертов отдельно доказано `promtool test rules`.
