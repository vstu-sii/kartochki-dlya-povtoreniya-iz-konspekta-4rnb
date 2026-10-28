# Фриз production перед Demo Day

- Публичный сервис: https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com
- Проверка: https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com/health
- Версия и дата демо: ещё не подтверждены.
- Начало фриза: **не объявлено**.
- Ответственная за фриз и Plan B: Delivery — Ермакова Алиса

Этот документ — план и не является объявлением фриза. После согласования даты
команда должна объявить фриз не позднее чем за сутки до демо. С начала фриза запрещены deploy, изменение переменных Render и
перемещение тега. Исключение — только критический инцидент, при котором основной
сценарий невозможно показать; решение и причина фиксируются отдельным commit.

Перед фризом Delivery выполняет:

```bash
python scripts/demo-seed/reset_demo.py
python scripts/demo-rehearsal.py --public-url https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com
```

В день демо выполняется только чтение `/health`, открытие Telegram-бота,
локального видео и dashboard. Новых deploy в день показа нет.
