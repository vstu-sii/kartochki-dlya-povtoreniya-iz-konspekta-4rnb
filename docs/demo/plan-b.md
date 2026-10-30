# План Б для Demo Day

## Основной сценарий

1. Открыть публичный URL и показать `/health`.
2. В Telegram открыть бота, выполнить `/start`, отправить подготовленный PDF.
3. Показать карточку с вопросом. В текущей версии Telegram источник и цитата пользователю не отображаются.
4. Ответить своими словами, показать смысловую проверку и перейти к следующей карточке.

## Если недоступен Gemini

Локальная имитация отказа проверяется командой `python scripts/demo-rehearsal.py`; результат хранится в `artifacts/demo/plan-b-rehearsal.json`. Это не проверка отказа через Telegram на проде.

## Если недоступен Wi-Fi или Render

1. Переключить ноутбук на заранее проверенный мобильный интернет.
2. Если сервис не восстановился за 30 секунд, показать [новое видео Product](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/blob/lab6-product-demo/docs/demo/video-demo.mp4). До демо скачать его на ноутбук и флешку и проверить воспроизведение без сети. Это ещё не подтверждено.
3. Объяснить, что показана запись.

## Быстрая команда локальной репетиции

```bash
python scripts/demo-seed/reset_demo.py
python scripts/demo-rehearsal.py --public-url https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com
```

Скрипт проверяет локальную симуляцию fallback, публичный `/health` и старый файл `docs/demo/demo-backup.mp4`, а не новое видео Product. Воспроизведение нового видео нужно проверить отдельно.
