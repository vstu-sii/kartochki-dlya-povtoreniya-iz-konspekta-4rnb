# Нагрузочное тестирование Lab 5

```powershell
python tests/load/run_load_test.py --base-url https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com --levels 1,5,10,20,40 --requests-per-level 20
```

SLO: error rate ≤1%, p95 `/health` ≤2000 мс. Полный результат лежит в `artifacts/load/lab5-load-results.json`. `verified_sustainable_concurrency` — подтверждённая нижняя граница, `first_failed_concurrency` — первый проваленный уровень. Если провала нет, отчёт честно фиксирует нижнюю границу, а не выдуманный максимум.

Фактический прогон 18.10.2026: уровни 1/5/10/20/40, по 10 запросов; **0 ошибок**, p95 от **805 до 1537 мс**. Предел по SLO не достигнут: подтверждённая производительность — **не менее 40 одновременных запросов к health endpoint**. Это предел измерения текущего безопасного теста, не обещание пропускной способности генерации Gemini.
