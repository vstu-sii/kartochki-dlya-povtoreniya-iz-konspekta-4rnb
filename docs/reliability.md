# Надёжность публичного прототипа

```powershell
python tests/reliability/measure_prod.py --url https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com/health --samples 30 --interval 1
```

`artifacts/reliability/prod-window.json` хранит каждую пробу, границы периода, uptime, p50 и p95. Это короткое контрольное окно Lab 5, не имитация недельного SLA; для Demo Day его дополняет история Render/Grafana.

Фактическое окно 19.10.2026 (`2026-10-18T22:48:44Z`—`22:49:40Z`): 30/30 успешных проб, **uptime 100%**, p50 **793,83 мс**, p95 **2437,77 мс**. Артефакт содержит все 30 проб. Это короткое активное измерение доступности, поэтому оно не доказывает месячный SLA; повышенный p95 остаётся ограничением бесплатного Render-инстанса.
