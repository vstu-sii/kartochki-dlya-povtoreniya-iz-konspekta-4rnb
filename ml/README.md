# ML / AI Service — передача следующему инженеру

Рабочая реализация находится в `ml/models/baseline.py`. `BaselineModel.generate()` строит grounded-карточки, `BaselineModel.review()` оценивает свободный ответ. При `MODEL_PROVIDER=gemini` и наличии `GEMINI_API_KEY` вызывается Gemini; сетевой отказ, timeout, неверный JSON или исчерпание квоты переводят запрос на deterministic fallback. Все вызовы проходят через `TraceClient`, секреты и полный текст по умолчанию не пишутся.

Контракт HTTP: `api/openapi.yaml`. Эндпоинты приложения: `backend/routers/ai.py`. Версионируемые prompts: `ml/prompts_v2/`. Read-only инструмент поиска: `ml/tools/`. Evals: `tests/evals/`. Полный релизный прогон: `python tests/evals/run_release_evals.py --release-ref WORKTREE`; ablation: `python -m ml.experiments.run_ablation`.

Основные переменные окружения: `MODEL_PROVIDER`, `GEMINI_API_KEY`, `LLM_PRIMARY_MODEL`, `LLM_CHEAP_MODEL`, `GEMINI_TIMEOUT_SECONDS`, `GEMINI_MAX_ATTEMPTS`, `SOURCE_TOOL_TIMEOUT_SECONDS`, `TRACE_CONTENT`. Значения и безопасные defaults находятся в `.env.example`; ключи в git не добавляются.

Стабильные выходы соответствуют схемам `CardSet` и `AnswerReview`; дополнительно возвращаются `model`, `prompt_version`, `trace_id`, `latency_ms`, `usage`, `fallback_used`, `fallback_reason`, а для генерации — `tool_status`. Инструмент не имеет сети, записи в БД и необратимых прав. Его timeout/forbidden/error/empty обрабатываются безопасным fallback на страницы текущего запроса.

Факты релиза `v0.5.0`: schema и grounding 100%, review agreement 92,86%, provider A/B на `gemini-3.5-flash-lite` — 95% у A и 100% у B; цена B — 6380 против 3843 токенов. Локальная deterministic latency не является latency Gemini. Известные ограничения: provider A/B содержит 20 кейсов и один прогон, OCR зависит от качества PDF, кэш и limiter process-local.
