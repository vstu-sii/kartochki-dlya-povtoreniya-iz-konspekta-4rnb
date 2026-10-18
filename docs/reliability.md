# Надёжность публичного прототипа

```powershell
python tests/reliability/measure_prod.py --url https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com/health --samples 30 --interval 1
```

`artifacts/reliability/prod-window.json` хранит каждую пробу, границы периода, uptime, p50 и p95. Это короткое контрольное окно Lab 5, не имитация недельного SLA; для Demo Day его дополняет история Render/Grafana.

Фактическое прогретое окно 18.10.2026: 10/10 успешных проб, **uptime 100%**, p50 **757,50 мс**, p95 **829,81 мс**. Предварительное окно при пробуждении Render дало 8/10 и p95 15,46 с — это зафиксированный cold-start риск бесплатного инстанса, а не удалённая «неудобная» цифра.
