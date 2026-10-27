# Передача AI-части

## Текущее проверенное окружение

Production-кандидат: `v0.5.5-integrated-candidate`, SHA `bc56b605aaa7a9781fefd1bc576eb0d59bb20301`. В Render `MODEL_PROVIDER=gemini`, основная и экономичная модель — `gemini-3.5-flash-lite`; ключ задаётся только секретом окружения. После смены модели повторите quality evals: предыдущий deterministic gate не измеряет Gemini. При некорректном выводе генерации предусмотрена одна повторная попытка, отклонённая цитата не принимается, fallback не кэшируется. Сценарий проверки и исходные результаты: `tests/evidence/run_production_handoff.py`, `artifacts/quality/lab5-production-final/gemini-formula-bc56.json`; для повторения потребуется доступный ключ в среде приложения. Сравните модель, SHA, fallback и usage в ответе; текущее приложение не раскрывает текст промпта в trace по умолчанию.

## Контракт

`BaselineModel.generate(payload)` возвращает CardSet со ссылкой на страницу/цитату; `review(payload)` возвращает `correct|partially_correct|incorrect`, score, feedback и missing points. Публичные маршруты описаны в `api/openapi.yaml`.

## Запуск и конфигурация

Без ключа: `MODEL_PROVIDER=deterministic`. С Gemini: `MODEL_PROVIDER=gemini`, секрет `GEMINI_API_KEY`, модели `LLM_PRIMARY_MODEL`/`LLM_CHEAP_MODEL`. Ключи никогда не хранятся в Git. Prompts версионируются в `ml/prompts_v2/`, схемы проверяются до сохранения.

## Путь запроса

API → token budget → source lookup → prompt/schema → Gemini → quality guards → fallback при временном отказе → trace → БД. Модель не пишет в БД и не выполняет необратимых действий; это делает приложение после проверок.

## Проверка

```bash
python tests/evals/run_evals.py --output artifacts/evals/lab5-final-results.json
python tests/evals/run_application_evals.py
python -m ml.experiments.run_ablation
python -m tests.evals.prepare_lab1_quality_evidence
```

Первый прогон подтверждает 95 модельных кейсов и 12 input guards, второй — 37 application/DB-кейсов. Полный командный gate одной командой: `python tests/evals/run_full_suite.py`.

Смотреть: `docs/ml-final-metrics.md`, `docs/experiments/lab5.md`, `docs/quality/lab1-ai-evidence.md`, trace-конфиг `ml/tracing/`. Известные ограничения: один PDF, OCR зависит от качества скана, top-3 retrieval теряет четвёртый релевантный фрагмент, provider A/B мал и требует повторов перед коммерческим SLA. Критерии Lab 1, требующие исходных PDF, ручной разметки и live-среды, остаются открытыми до совместного замера и не подменяются локальным deterministic-runner.

## Повторная проверка deterministic-review-v5

После совместного ревью Quality улучшено смысловое сопоставление ответов и формирование `feedback`/`missing_points`. Старые подтверждённые результаты сохранены отдельно, а новый набор тех же `REV-001…REV-020` подготовлен для повторной ручной проверки:

```powershell
py -3 -m tests.evals.prepare_lab1_quality_evidence --output artifacts/evals/lab1-ai-quality-evidence-after-fix.json
```

Подробности, команды и автоматические результаты находятся в `docs/quality/lab1-ai-evidence-after-fix.md`. Поля нового ручного ревью намеренно пустые: итоговые продуктовые проценты считает Quality совместно с AI Engineer.

## Проверка карточек из реального PDF

`deterministic-grounded-v2` сначала объединяет визуальные переносы строк PDF и только затем выделяет законченные предложения и пункты списка. Поэтому перенос строки по ширине страницы больше не создаёт отдельную карточку.

Повторный прогон того же PDF из Quality-ветки:

```powershell
py -3 tests/evals/run_pdf_card_quality.py --git-object origin/lab5-quality-testing:tests/fixtures/lab5-devops-source.pdf --output artifacts/evals/lab5-devops-pdf-cards-after-reflow.json --count 5
```

Автоматические проверки подтверждают только привязку цитаты к странице и отсутствие очевидного обрыва. Процент верных тезисов Quality считает вручную по полям `quality_manual_review`, которые генератор намеренно оставляет пустыми.


## Сохранение формул PDF — 27.10.2026

Для насыщенных математикой векторных страниц extractor восстанавливает индексы, дроби и корни по геометрии PDF в явную текстовую запись (`math_layout`). Справочные формулы не подставляются, исходные опечатки сохраняются. Модель цитирует именно переданный нормализованный текст страницы. Обычная проза и OCR используют прежний путь.

Воспроизведение: `python tests/evals/run_formula_quality.py`, затем `python tests/evals/run_full_suite.py`. На PDF из 39 формул сохранены 39/39 при извлечении и исчерпывающей генерации по батчам <=10. Реальный локальный API полного PDF: 201, пять карточек в SQLite. [Доказательства и ограничения](../artifacts/ai/formula-fix-2026-10-27/README.md). Это локальный результат на одном PDF, не проверка произвольного OCR или production.
