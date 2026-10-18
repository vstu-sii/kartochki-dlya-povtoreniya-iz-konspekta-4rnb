# Штатная деградация Lab 5

| Отказ | Поведение | Ответ |
|---|---|---|
| AI service timeout/network/5xx | две попытки с паузой, затем остановка | `503 AI_PROVIDER_UNAVAILABLE` |
| AI service 4xx | без бессмысленного повтора | исходный 4xx |
| БД недоступна | транзакция не считается успешной | `503 DATABASE_UNAVAILABLE`, `Retry-After: 5` |
| Gemini недоступен внутри AI service | grounded deterministic fallback из ADR-002 | `fallback_used=true` |

Таймаут задаёт `AI_TIMEOUT_SECONDS` (65 с), число попыток — `AI_MAX_ATTEMPTS` (2, максимум 3). Результат сохраняется только после валидного ответа и quality guards. Проверка сетевого отказа: `tests/test_lab5_failures.py`.
