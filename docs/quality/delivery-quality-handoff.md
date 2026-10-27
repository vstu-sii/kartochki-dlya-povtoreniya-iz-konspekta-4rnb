# Delivery → Quality: Lab 5 handoff

Дата: 27.10.2026. Доказательства относятся к проверочному кандидату и не означают, что все критерии приёмки закрыты.

## Общая версия и релизный прогон

- Интеграционная ветка `lab5-integrated-quality`: Delivery `d49a42e`, AI `9d29cf2` (включает `205e740`) и Quality `9685b3e`; конфликтующие отчёты сохранены в версии Quality, AI-тесты сохранены.
- Неизменяемый тег-кандидат `v0.5.3-quality-candidate`, коммит `85b546e20f54a97f11dea1ac295e679902fc2b46`. Старые теги не перемещались. Это кандидат: Gemini-проверка ещё не пройдена.
- [Полный релизный quality run на теге](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/40554481097): success. JSON и логи — в артефакте этого запуска; режим `MODEL_PROVIDER=deterministic`, не живой Gemini.
- [Сборка релизного тега](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/40554480700): success.
- [Дополнительный интеграционный run на теге](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/40554480687): failure на привязке отчёта к тегу из-за изменённых во время прогона файлов результатов; сам полный набор прошёл, Grafana job прошёл. Причина исправлена в следующем коммите ветки; данный run нельзя выдавать за зелёный. Обычный [branch run](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/40552404953) был success.

## Grafana

- Реальный снимок работающего Compose-стенда: [grafana-integrated.png](evidence/lab5/grafana-integrated.png); [метаданные](evidence/lab5/grafana-integrated.json).
- 27.10.2026 17:47:50 UTC; диапазон последние 15 минут, окружение `ci-staging`, версия `lab5-integrated`, SHA `85b546e20f54a97f11dea1ac295e679902fc2b46`.
- Адрес во время работы стенда: `http://localhost:3001/d/flashcards-prod/flashcards-production-overview?orgId=1&from=now-15m&to=now`; GitHub Actions-стенд временный и после завершения недоступен извне. Снимок показывает запросы, 5xx, задержку, логи и трейсы; трафик сгенерирован тестовыми запросами, это не метрики production. На экране 5xx = 0 для показанной панели; ошибки 503 наблюдались на frontend и не должны трактоваться как захваченные этой панелью.

## Публичный стенд и диагностический прогон

- [Production URL](https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com), [Render deploy](https://dashboard.render.com/web/srv-daem63n40ujc73fq8sr0/deploys/dep-dbge7aavcj2c73ef7l30): на 27.10.2026 `/health` HTTP 200, SHA `85b546e20f54a97f11dea1ac295e679902fc2b46`, совпадает с тегом.
- Обычный и формульный тестовые PDF вернули HTTP 201 с пятью карточками при fallback. Одна обычная сессия создана HTTP 201, повторно открыта HTTP 200; пять ответов обработаны HTTP 200, у каждого ответ API содержит `persisted: true` и `review_id`.
- [Сырые обезличенные результаты диагностики](../../artifacts/quality/lab5-production-final/degraded-scenario.json), 27.10.2026 17:52 UTC: генерация — `gemini_http_503`, пять разборов — `gemini_http_429`; все шесть вызовов завершились deterministic fallback. Это не успешный Gemini-сценарий. Отдельный формульный запрос для `gemini-2.5-flash` вернул HTTP 201 с fallback `gemini_http_404`.
- В отчёте timings относятся к одному деградированному сценарию (1 генерация, 5 разборов); они не представляют устойчивый p95 Gemini. Подсчитанные fallback-токены являются оценкой приложения, не данными оплаты Gemini. Стоимость полного provider-сценария не установлена.
- Логи production за интервал прогона на повторный `MODEL_OUTPUT_INVALID` не проверены; отсутствие события не подтверждено.

## Осталось для Quality и AI

1. Владелец Gemini API проверяет в Google AI Studio доступные модели, квоту и ограничения ключа/проекта: ответы 429 и 503 не позволяют установить единственную причину без данных провайдера. Ключ не передавать и не помещать в Git.
2. После восстановления Gemini выполнить обычный и формульный PDF, полный сценарий с пятью ответами и серию сценариев без fallback. Сохранить provider-токены, времена, реальные тарифы и расчёт стоимости с размером выборки p95.
3. Проверить логи production за измеренный интервал. После любого изменения кода/конфигурации зафиксировать и проверить новую версию, при необходимости создать новый тег и повторить полный CI. Данный кандидат не считать финально принятым до завершения живого прогона.
