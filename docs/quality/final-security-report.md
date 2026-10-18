# Финальная повторная проверка безопасности

После исправлений повторно запущен `python tests/security/run_attacks.py --mode after`. Результат `artifacts/security/lab4-attacks-after.json`: **14/14 атак заблокированы**, 0 пробившихся. Проверены prompt injection, подмена source/эталона, tenant/session access, опасные поля, budget/idempotency и права model tool.

| Риск | До контроля | После | Решение |
|---|---|---|---|
| Injection из PDF/ответа | высокий | низкий | untrusted-input + grounding/schema/policy gates |
| Подмена эталона клиентом | высокий | низкий | эталон читается из БД |
| Чужая сессия/карточка | высокий | низкий | owner/session checks |
| Необратимое действие модели | высокий | низкий | модель только предлагает, приложение авторизует/пишет |
| Перерасход токенов | средний | низкий | server-side budget, alert и cheap tier |

Остаточный риск: adversarial binary PDF/OCR и полноценная authentication не покрыты текущим HTTP-набором. Это не скрывается зелёной средней метрикой; до публичной продажи нужны отдельный parser fuzzing и Telegram login/session token.
