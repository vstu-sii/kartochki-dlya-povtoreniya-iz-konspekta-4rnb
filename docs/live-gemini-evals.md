# Живой Gemini golden eval

`MODEL_PROVIDER=gemini python tests/evals/run_evals.py --require-provider --min-schema 1 --min-grounding 1 --min-review .85 --min-safety 1 --output artifacts/evals/live-gemini-results.json`

GEMINI_API_KEY должен быть в окружении, никогда в команде/файле Git. LLM_PRIMARY_MODEL и LLM_CHEAP_MODEL задают фактическую модель. Без ключа runner сохраняет blocked-отчёт и возвращает 2. При fallback/кешированном ответе provider_success_rate <1 и gate красный, даже если детерминированный ответ совпал с эталоном.

GitHub Actions: **Lab5 live Gemini golden evals → Run workflow → ветка lab5-ai-testing**, mini=false для полного модельного поднабора. Нужен repository secret GEMINI_API_KEY. Запуск платный/расходует квоту; workflow только ручной. Артефакт сохраняется и при ошибке. Добавлять ключ в PR или передавать Quality не нужно.

Проверяются все generation/review кейсы и input guards из текущего dataset; API/DB cases отмечаются skipped и проверяются `run_full_suite.py` отдельно. Этот прогон нельзя называть 132 живыми LLM-вызовами: guards исполняются локально, API/DB отдельным runner. Ответы, model/fallback/trace и usage сохранены по кейсам для проверки качества своими словами; автоматическое agreement не заменяет ручной смысловой аудит объяснений.

На 27.10.2026 локального GEMINI_API_KEY нет, поэтому полный живой golden не выполнен. Создание workflow не означает успешный прогон. Исторические v0.5.7 и 12,582 с относятся к cards-v2.2; новый cards-v2.3 требует новой проверки после выкладки.
