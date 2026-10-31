# Переход на aiogram

Ветка feature/aiogram-integration. Архивные теги лабораторных не перемещаются.

Новый пакет bot/ перенесён из отдельного flashcards-aiogram-bot. telegram_bot/app.py теперь адаптер aiogram: standalone long polling в Compose и Dispatcher.feed_update через существующий FastAPI webhook на Render. На старте webhook не удаляет накопленные сообщения. Работать должен только один экземпляр с данным Telegram-токеном.

Новые таблицы tg_users, tg_decks, tg_cards, tg_reviews не конфликтуют с прежними cards и study_sessions. На старте импортируются наборы, привязанные к Telegram-сессиям; импорт идемпотентный, чужие владельцы не объединяются, исходные строки не удаляются. Старые ответы и оценки остаются в старых таблицах; расписание интервальных повторений создаётся заново. Перед production сделайте backup DATABASE_URL. Если старая БД была в эфемерном /tmp и уже потеряна, импорт не восстановит удалённые данные.

Compose использует прежний postgres-data volume. Все сервисы получили restart: unless-stopped. Сервисы с healthcheck помечены для Autoheal, который перезапускает unhealthy-контейнеры. Autoheal получает административный доступ к Docker через docker.sock; предназначен для доверенного локального Docker-хоста. Render не запускает Compose: он использует Dockerfile и собственную проверку /health.

Локально: docker compose up -d --build. Проверка: docker compose ps и docker compose logs autoheal telegram-bot. Новому боту необходим GEMINI_API_KEY; GEMINI_MODEL выбирайте доступный вашему ключу (на Render также учитывается LLM_PRIMARY_MODEL). Режимы AI-библиотеки и прежнего backend не смешиваются: aiogram вызывает Gemini напрямую асинхронно. Старые HTTP API сохранены для прежних клиентов.

Для production нужен постоянный PostgreSQL DATABASE_URL. Напоминания требуют работающего без сна экземпляра. Разбор PDF в новом боте подключён к прежнему OCR и обработке формул через asyncio.to_thread. Образы включают Tesseract и зависимости. Требуются ручная приёмка и проверка webhook после переключения.

Меню: Мои наборы / Повторить / Загрузить PDF / Прогресс / Напоминания / Помощь. Напоминания выключены по умолчанию; пользователь включает сам. Источник и цитата в сообщениях не показываются.
