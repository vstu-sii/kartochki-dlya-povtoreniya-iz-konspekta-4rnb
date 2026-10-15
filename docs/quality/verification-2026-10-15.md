# Техническая проверка Lab3 — 15.10.2026

Проверки выполнены локально автоматически, Python 3.14.3, deterministic provider, SQLite. Это технический протокол; ручной проход UC выполнен отдельно внешним студентом Постернаком Денисом 15.10.2026 (`docs/use-cases/validation-lab3.md`).

| Проверка | Результат |
|---|---|
| Mini: GEN-001…004, REV-004/005, SAFE-001/002 | 8 кейсов: 4 generation, 2 review, 2 safety; все пороги пройдены |
| Full model | 95 модельных кейсов, review agreement 90,48%, schema/grounding 100% |
| Application eval | 33/33; реальные функции guard/router и SQLite |
| HTTP regression | Пустой/пробельный ответ → 422; превышение токенов и PDF >40 страниц → 413; модель не вызвана |
| Сессии HTTP | Нет X-User-ID → 401, другой владелец → 403, совпадающий владелец → 200 |
| Короткий документ | Один уникальный тезис → одна карточка вместо пяти повторов |

В сумме пройдены 6 unittest-тестов в Delivery. Unit/HTTP-тесты используют локальный TestClient, а не браузер или Telegram. Docker, PostgreSQL и публичный UI в этом локальном прогоне не проверялись; их отдельное доказательство — Delivery CI после push.

## Границы подтверждения

- X-User-ID обязателен для чтения сессии по ID, progress, ratings и complete. Это заявленная клиентом идентичность, а не авторизация: серверная аутентификация и защита создания/resume сессий остаются открытым риском. Не заявляем полноценную защиту от подмены пользователя.
- Mini safety вызывает тот же guard, который использует backend; HTTP-регрессии дополнительно проверяют подключение валидации к endpoint.
- Общие 128 кейсов не означают browser E2E: модельный и прикладной наборы проверяются раздельно.
- Evals используют оценку токенов, не фактическую стоимость Gemini.
- Внешняя приёмка UC (Постернак Денис), ревью восьми новых golden-кейсов и согласование спринта 4 зафиксированы в `team-acceptance-lab3.md` и `validation-lab3.md`.
- Scheduled GitHub Actions начнёт выполняться автоматически только после включения workflow в default branch. Пока доступны push/PR mini; full можно воспроизвести командой из README.

## GitHub Actions после отправки исправлений

Проверено 15.10.2026:

- Delivery, commit `2ea18f7`: https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/38742025891 — success. Прошли установка зависимостей, unit/HTTP, 33 прикладных кейса, Compose config/up, доступность frontend и tracing, сквозной HTTP smoke-test через gateway с моделью и PostgreSQL.
- AI, commit `245f1a4`: https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/38742026317 — success; unit/HTTP и mini с отдельными порогами.
- Quality, commit `a9cfb89`: https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/38742025869 — success; unit/HTTP и mini 4 generation + 2 review + 2 safety.

HTTP smoke-test не управляет браузером: проверка frontend — HTTP-доступность страницы, дальнейшие действия выполняются через API gateway. Это автоматическое доказательство интеграции, не внешний ручной проход интерфейса.

Публичный `/health` в дополнительной проверке не ответил за 15 секунд. Это не доказывает поломку сервиса, но актуальную доступность production этим запросом подтвердить не удалось. Более ранняя отметка доступности в протоколе относится к предыдущей проверке.


Дополнение по ручным материалам: 15.10.2026 внешний студент **Постернак Денис** прошёл UC-01…UC-05 на живом Telegram-боте; получены шесть скриншотов, ревью восьми новых эталонов и согласование плана спринта 4. Актуальная запись — [протокол свидетельств](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/blob/lab3-product-prototype/docs/quality/evidence/2026-10-15/README.md) и [`docs/use-cases/validation-lab3.md`](../use-cases/validation-lab3.md). Автоматические результаты выше остаются автоматическими и не подменяют ручной проход.
