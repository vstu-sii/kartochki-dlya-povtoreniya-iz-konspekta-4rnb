# Фриз production перед Demo Day

- Публичный сервис: https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com
- Проверка: https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com/health
- Версия для демо: тег `v0.5.2-demo`, commit `af194ff`
- Начало фриза: **28.10.2026, 12:00 (Europe/Volgograd)**
- Плановое демо: **29.10.2026, 14:00 (Europe/Volgograd)**
- Ответственная за фриз и Plan B: Delivery — Ермакова Алиса

Запись в репозитории является объявлением команде более чем за сутки до
планового показа. С начала фриза запрещены deploy, изменение переменных Render и
перемещение тега. Исключение — только критический инцидент, при котором основной
сценарий невозможно показать; решение и причина фиксируются отдельным commit.

Перед фризом Delivery выполняет:

```bash
python scripts/demo-seed/reset_demo.py
python scripts/demo-rehearsal.py --public-url https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com
```

В день демо выполняется только чтение `/health`, открытие Telegram-бота,
локального видео и dashboard. Новых deploy в день показа нет.
