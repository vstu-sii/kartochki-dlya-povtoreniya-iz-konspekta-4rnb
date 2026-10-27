# Q5-PDF-02: исправление PDF/API-контракта — 27.10.2026

База: AI 2076016532294192e28a0ea7df6e1a916ad6c307.
Причина 502: deterministic-генератор возвращал reflow-текст в source_quote, который не являлся точной подстрокой исходной страницы.

Исправлено: reference_answer остаётся читабельным; source_quote восстанавливается как оригинальный непрерывный span PDF с исходными пробелами и переносами (до 500 символов). Строгий backend guard не изменён. Несопоставимый текст отвергается.

Проверка: `python -m unittest discover -s tests -p test_pdf_generation_contract.py -v` — 3 теста, включая реальный multipart POST /v1/ai/card-sets/from-pdf: 201 и 5 карточек в изолированной SQLite. Дополнительно проверяются переносы, лимит цитаты и отказ для выдуманной цитаты.
`python tests/evals/run_full_suite.py` — 8/8 групп, 132/132 уникальных кейса, 44 unit/integration-теста OK.
`python tests/evals/run_pdf_card_quality.py --pdf tests/fixtures/lab5-devops-source.pdf --output artifacts/ai/pdf-api-502-fix-2026-10-27/pdf-card-quality.json --count 5` — grounding 5/5, завершённость 5/5.

Проверен локальный deterministic/inprocess режим, не production и не платный Gemini. Прежние логи ошибки сохранены в Quality. Новый релизный тег и выкладка не выполнялись.
