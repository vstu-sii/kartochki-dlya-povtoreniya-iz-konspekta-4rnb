# Фактические quality gates лабораторной 4

| Набор | Фактический результат | Порог |
|---|---:|---:|
| Model schema | 100% | 100% |
| Grounding | 100% | 100% |
| Review agreement | 90,48% | ≥85% |
| Model cases | 95 выполнено | все применимые |
| API/DB cases | 33/33 | 100% |
| Security before | 10/10 атак пропускались политикой Lab3 | диагностика |
| Security after | 10/10 атак блокируются; 2/2 control разрешены | 100% совпадения |
| Lab4 limits/guards/tool tests | 6/6 | 100% |

Команды:

```bash
python tests/evals/run_evals.py --min-schema 1 --min-grounding 1 --min-review .85 --output artifacts/evals/lab4-full-results.json
python tests/evals/run_application_evals.py
python tests/security/run_attacks.py --mode after --output artifacts/security/lab4-attacks-after.json
python -m unittest -v tests.test_lab4_limits tests.test_lab4_guards tests.test_lab4_tool
```

Quality gate не использует `GEMINI_API_KEY`: он воспроизводим и не отправляет учебные материалы наружу. Provider eval остаётся отдельным разрешённым измерением.
