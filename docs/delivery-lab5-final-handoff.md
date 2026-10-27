# Delivery: актуализация ролевой ветки Lab5

Общая проверенная версия 5504ef5 и исправления AI синхронизированы в lab5-delivery-testing. Документы после тега не выдаются за содержимое старого тега; существующие теги не перемещались. Новый релиз не создавался и не выкладывался этим обновлением.

API передаёт безопасную категорию validation_error и provider_usage отклонённых попыток, если они предоставлены AI. Скрипт tests/evidence/run_production_handoff.py сохраняет текущую генерацию и каждый review **до** проверки успешности, при ошибке пишет status=failed и возвращает 1. Копия эталона явно называется reference_copy_not_paraphrase; доказательством качества ответов своими словами она не является.

Проверка после выкладки: `python tests/evidence/run_production_handoff.py --base-url https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com --scenarios 5 --fixture alternating --output artifacts/quality/provider-after-deploy.json`. Не добавляйте --allow-fallback для доказательства Gemini. Смотрите trace/validation_error при отказе; результаты всех неудачных попыток сохраняются. На публичном старом SHA новый промпт не проверяется.

Для полного живого model golden есть ручной workflow **Lab5 live Gemini golden evals**, секрет GEMINI_API_KEY. Перед созданием нового тега выполнить полный deterministic gate. После новой выкладки сохранить SHA /health, версии cards-v2.3/review-v2.1, новый полный CI, логи и серию p95. На прошлой версии e88 p95=12,582 с >7 с; обещания ускорения нет. Minimal-thinking эксперимент остаётся неудачным, его данные не удалять.

Обычный CI/Grafana теперь запускается также при push в три ролевые ветки, а живой Gemini — только вручную. Production-логи и повторный provider-прогон требуют доступа владельца стенда; они не выдумываются.


После синхронизации общий локальный прогон: 8/8 групп и 132/132 кейса. Лог unit/integration: [файл](../artifacts/quality/lab5-role-sync-2026-10-27/unit-and-integration.log). Все эти проверки используют deterministic/model mocks; это не новый живой Gemini и не production выкладка.
