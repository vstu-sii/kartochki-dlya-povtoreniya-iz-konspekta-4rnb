# Delivery: Demo Day

| Критерий | Доказательство |
|---|---|
| Публичный прод на релизном теге | Кандидат `v0.5.10-demo-candidate` указывает на `a60eee706ad17238c11e0c79f53f026fd68bdf81`, совпавший с публичным `/health` 29.10.2026. [Release quality gates](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/40919274884) и [сборка](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/40919274864) прошли. Перед демо повторить проверку. |
| Демо-данные и сброс одной командой | `scripts/demo-seed/reset_demo.py`; повторный запуск проверяется тестом |
| Деградация и видео-бэкап | `scripts/demo-rehearsal.py`, `artifacts/demo/plan-b-rehearsal.json`, `demo-backup.mp4` |
| Фриз за сутки | `release-freeze.md`: объявлен в репозитории 29.10.2026 в 23:24 по Волгограду; получение командой отдельно не подтверждено. |

Это Delivery-артефакты. Сценарий выступления, финальные слайды и публикация
внешней ссылки на видео принадлежат Product, а модельные кейсы — AI Engineer.

28.10.2026 повторный локальный сброс в отдельной SQLite-БД дважды вернул 5 карточек, одну сессию и одну оценку; это не проверка наполнения production. Файл `demo-backup.mp4` декодируется, длительность 126 секунд, кадры меняются; происхождение записи с текущего прода и воспроизведение со звуком пока не подтверждены.

29.10: Render Shell недоступен на бесплатном тарифе, поэтому сброс в production не выполнен. [Промо Product](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/blob/lab6-product-demo/docs/demo/telegram-promo.mp4) сделано на предыдущем SHA `1b320e1`, до скрытия цитат в Telegram; оно не является видео текущего интерфейса.

После фриза выполнен [публичный API-сценарий](../../artifacts/demo/lab6-public-a60.json): обычный PDF, 5 карточек, 5 ответов и повторное открытие сессии; все вызовы Gemini без fallback, сохранение подтверждено ответом API. Ответы повторяли эталон и это не прогон Telegram или сброс тестовых данных. P95 пяти ответов 1,914 с; эта малая выборка не доказывает стабильность и не отменяет прежний замер 31,990 с.


**Актуализация:** основной видеобэкап Product — [video-demo.mp4](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/blob/lab6-product-demo/docs/demo/video-demo.mp4); предыдущие сведения выше относятся к старым роликам. Новое видео необходимо скачать и проверить офлайн до демо.
