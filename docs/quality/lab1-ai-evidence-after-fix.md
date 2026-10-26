# Повторная проверка deterministic-разборов после исправлений

**Дата:** 26.10.2026  
**Объект:** те же 20 кейсов `REV-001…REV-020`  
**Реализация:** `deterministic-review-v3`  
**Статус ручной проверки:** ожидается совместное ревью AI Engineer и Quality

## Что исправлено

- Смысловые эквиваленты больше не считаются пропусками: RAM и оперативная память; общая и разделяемая память; ограничение одним потоком.
- Добавлены отрицательные проверки, чтобы смысловые эквиваленты не принимали ответы про жёсткий диск, раздельную память, несколько потоков и LIFO вместо FIFO.
- `REV-012` оценивается как полный ответ: TLS и защита данных покрывают записанный обязательный пункт.
- В `feedback` теперь указывается, что в ответе верно, что неверно и какой правильный смысл нужен.
- `missing_points` содержит полные смысловые пункты вместо обрезанных основ слов.
- Для `REV-015` в эталоне явно закреплено требование назвать термин FIFO; отсутствие термина объясняется именно так.
- Изменения эталонов `REV-012`, `REV-015` и `REV-018` отдельно обоснованы в `docs/quality/golden-dataset/review-log.md`.

## Артефакты

- Результат до исправлений: `artifacts/evals/lab1-ai-quality-evidence-before-fix.json`.
- Подтверждённый протокол до исправлений: `docs/quality/lab1-ai-evidence-review-before-fix.md`.
- Новый результат для повторного ревью: `artifacts/evals/lab1-ai-quality-evidence-after-fix.json`.
- Генератор: `tests/evals/prepare_lab1_quality_evidence.py`.
- Полный регрессионный отчёт: `artifacts/evals/full-suite-results.json`.
- Отдельный модельный отчёт после исправлений: `artifacts/evals/lab5-final-results-after-review-fix.json`.

Новый JSON содержит входы, эталоны, обязательные пункты, `verdict`, `score`, `feedback`, `missing_points`, модель, версию промпта, trace и token usage. Все поля `quality_manual_review` оставлены пустыми для совместной повторной проверки.

## Воспроизведение

```powershell
py -3 -m tests.evals.prepare_lab1_quality_evidence --output artifacts/evals/lab1-ai-quality-evidence-after-fix.json
py -3 -m unittest tests.test_baseline tests.test_lab1_quality_evidence -v
py -3 tests/evals/run_evals.py --output artifacts/evals/lab5-final-results-after-review-fix.json --min-schema 1 --min-grounding 1 --min-review .90 --min-safety 1
py -3 tests/evals/run_application_evals.py
py -3 tests/evals/run_full_suite.py
```

## Результаты автоматических проверок

- Точечные проверки исправления: 12/12 успешно.
- Все unit/integration-тесты: 36/36 успешно.
- Application/API/DB eval: 37/37 успешно.
- Model/guard eval: schema 100%, grounding 100%, review agreement 92,86%, safety 100%.
- Полный gate: 8/8 наборов успешно; выполнены все 132 уникальных кейса, пропусков нет.
- Автоматическое совпадение ожидаемого `verdict` на `REV-001…REV-020`: 20/20. Это техническая проверка и не заменяет ручную оценку качества объяснений.

## Что должен подтвердить Quality

Quality повторно заполняет пустые поля `quality_manual_review` во всех 20 строках и считает:

- отсутствие противоречий: минимум 18/20;
- полнота объяснений: минимум 16/20;
- критические нарушения тона: 0;
- мелкие нарушения тона: не более 1/20.

До этого ручного ревью нельзя утверждать, что продуктовые пороги достигнуты.

## Версия кода

В новом JSON записан базовый локальный SHA `d80f485e0543efccd186dd8bd8a67f9293e10470` и `working_tree_clean=false`, потому что исправления пока не закоммичены по просьбе владельца ветки. После согласованного локального коммита JSON нужно перегенерировать, чтобы передать Quality окончательный SHA проверенной версии.
