# Quality gates Lab4 — фактический статус 17.10.2026

Полная команда: `python tests/evals/run_full_suite.py`.
Среда фактической локальной перепроверки: Python 3.11, `MODEL_PROVIDER=deterministic`.
Установка: `python -m pip install -r backend/requirements.txt`.

## Что проверяется

| Набор | Измерение | Порог / результат |
|---|---|---|
| Golden v3 | 120 + 8 + 4 = 132 уникальных кейса | 132 исполнены; это охват, а не 132 успешных ответа |
| Model schema / grounding | 95 модельных кейсов | 100% / 100%, проходят пороги 1.0 / 1.0 |
| Review agreement | 38/42 | 90,48%, порог 85%; четыре расхождения остаются |
| Input safety guards | 12 reject_input | 12/12, порог 100%; не равнозначно всей безопасности |
| Application / DB / budget / timeout | 37 кейсов | 37/37; TOOL-L4-001: 5,664 мс при лимите 200 мс |
| Security after | 13 текстовых сценариев + replay | 14/14; ATK-011 и Q4-AUTH-01 проходят |
| Retrieval | 10 запросов | hit@1=100% (порог 90%), recall@3=100% (порог 100%), MRR=1 |
| Unit / integration | 29 тестов | 29 успешны |
| Общий gate | Все задания + полнота покрытия | **зелёный локально и в GitHub Actions**, 132/132 уникальных ID, exit code 0 |

Источник актуальных чисел — JSON на этом же коммите, а не исторический baseline.
`full-suite-results.json` объединяет статусы и проверяет ID всех golden-кейсов.
Модельный runner выполняет 95 модельных и 12 guard-кейсов (107), прикладной — 37.
12 guard-кейсов пересекаются: 107 + 37 − 12 = 132. Повторения не увеличивают охват.
Неизвестная операция, отсутствующий файл/ID, провал порога или сбой runner дают ошибку.
JSON предыдущего прогона удаляется перед соответствующим заданием: старый зелёный файл не подменяет отсутствующий новый.

## Mini и full

Mini сохраняет ровно восемь ID: GEN-001…004, REV-004, REV-005, SAFE-001, SAFE-002.
`--min-safety 1` — доля 100%, а не число кейсов.
Формула safety одинакова: успешные reject_input / выполненные reject_input;
в mini знаменатель 2, в полном модельно-защитном прогоне 12. Метрика больше не null.
Обход перефразированием и доступ к данным имеют отдельные router/security-проверки;
успешные 12 guards не подменяют эти проверки.

```bash
python tests/evals/run_evals.py --mini --min-schema 1 --min-grounding .95 --min-review .85 --min-safety 1 --output artifacts/evals/mini-results.json
python tests/evals/run_full_suite.py
```

## CI и запрет merge

`.github/workflows/quality-gates.yml` запускается на PR, push Lab4/main и вручную.
Все наборы исполняются даже при провале предыдущего; общий exit code сохраняет провалы.
Артефакты и логи загружаются с `if: always()`.
Отдельного release-триггера нет: перед релизом запускается тот же workflow вручную.

Успешные проверки коммита `3760914`: [Lab4 full quality gates](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/38959398688) и [Lab4 CI](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/38959398794).

В GitHub требуется назначить job `full-evals` обязательной проверкой защищённой ветки.
main помечена protected, но точный список required checks не подтверждён доступным API.
Quality не изменяла настройки репозитория. До проверки настроек нельзя утверждать,
что красный job технически запрещает merge.

## Границы доказательства

Нет live-вызовов Gemini и измерения production SLA/стоимости.
p95 относится к локальной обработке кейсов; не сравнивается с пользовательским SLA генерации.
Четыре эталона Lab4 совместно проверены на командном аудите 16.10.2026.
Участники: Ткаченко София, Цвилева Вероника, Ермакова Алиса и Доброквашина Анастасия.
Ранее подтверждённые восемь Lab3 не изменены.
Открытые задачи и владельцы: [open-findings-lab4.md](open-findings-lab4.md).
