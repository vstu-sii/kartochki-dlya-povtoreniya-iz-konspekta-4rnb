# Переход на aiogram

Ветка feature/aiogram-integration. Архивные теги лабораторных не перемещаются.

Новый пакет bot/ перенесён из отдельного flashcards-aiogram-bot. telegram_bot/app.py теперь адаптер aiogram: standalone long polling в Compose и Dispatcher.feed_update через существующий FastAPI webhook на Render. На старте webhook не удаляет накопленные сообщения. Работать должен только один экземпляр с данным Telegram-токеном.

Новые таблицы tg_users, tg_decks, tg_cards, tg_reviews не конфликтуют с прежними cards и study_sessions. На старте импортируются наборы, привязанные к Telegram-сессиям; импорт идемпотентный, чужие владельцы не объединяются, исходные строки не удаляются. Старые ответы и оценки остаются в старых таблицах; расписание интервальных повторений создаётся заново. Перед production сделайте backup DATABASE_URL. Если старая БД была в эфемерном /tmp и уже потеряна, импорт не восстановит удалённые данные.

Compose использует прежний postgres-data volume. Все сервисы получили restart: unless-stopped. Сервисы с healthcheck помечены для Autoheal, который перезапускает unhealthy-контейнеры. Autoheal получает административный доступ к Docker через docker.sock; предназначен для доверенного локального Docker-хоста. Render не запускает Compose: он использует Dockerfile и собственную проверку /health.

Локально: docker compose up -d --build. Проверка: docker compose ps и docker compose logs autoheal telegram-bot. Новому боту необходим GEMINI_API_KEY; GEMINI_MODEL выбирайте доступный вашему ключу (на Render также учитывается LLM_PRIMARY_MODEL). Режимы AI-библиотеки и прежнего backend не смешиваются: aiogram вызывает Gemini напрямую асинхронно. Старые HTTP API сохранены для прежних клиентов.

Для production нужен постоянный PostgreSQL DATABASE_URL. Напоминания требуют работающего без сна экземпляра. Разбор PDF в новом боте подключён к прежнему OCR и обработке формул через asyncio.to_thread. Образы включают Tesseract и зависимости. Требуются ручная приёмка и проверка webhook после переключения.

Меню: Мои наборы / Повторить / Загрузить PDF / Прогресс / Напоминания / Помощь. Напоминания выключены по умолчанию; пользователь включает сам. Источник и цитата в сообщениях не показываются.

Проверенная реализация: 937e9cd316acd18ce5f925f913e6ae6944d40c16. CI: https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/41241827071 — success (15 tests, обе Docker-сборки, Compose config, health/OpenAPI smoke). Дополнительно локально 75 прежних unittest — OK.

01.11.2026: по запросу владельца начата замена production на aiogram; прежний фриз больше не является запретом на эту выкладку. Исторические записи Demo Day и теги сохранены. Render Deploy: dep-dbj5hv67bikc73efofgg. Итоговое состояние фиксируется отдельно после /health.

Итоговая проверка production, 01.11.2026 (после 00:11 по Волгограду): Render Deploy succeeded / Live; GET https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com/health -> 200, status=ok, commit_sha=937e9cd316acd18ce5f925f913e6ae6944d40c16, telegram_adapter=aiogram, telegram=webhook. Startup завершён без ошибки. Ручной пользовательский сценарий /start -> PDF -> карточки -> повторение после выкладки отдельно не подтверждён. Проверка восстановления unhealthy-контейнера на настоящем Docker-хосте ещё не выполнялась; CI проверил конфигурацию и сборки, но не имитацию unhealthy.

Production развёрнут на указанном коммите реализации. Более поздний коммит этой документации не меняет исходники запущенного приложения. PR не создавался; main и старые теги не перемещались.
