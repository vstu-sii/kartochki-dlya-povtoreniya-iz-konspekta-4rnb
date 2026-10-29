# Фриз production перед Demo Day

- Публичный сервис: https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com
- Проверка: https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com/health
- Дата демо: **31.10.2026**, время не указано; кандидат `v0.5.10-demo-candidate`, SHA `a60eee706ad17238c11e0c79f53f026fd68bdf81`.
- Начало фриза: **29.10.2026, 23:24 (Europe/Volgograd)**. Объявление опубликовано в этой ветке репозитория; получение командой отдельно не подтверждено.
- Ответственная за фриз и Plan B: Delivery — Ермакова Алиса

Фриз объявлен в репозитории до демо 31 октября, более чем за сутки до начала этих суток. С начала фриза запрещены deploy, изменение переменных Render и
перемещение тега. Исключение — только критический инцидент, при котором основной
сценарий невозможно показать; решение и причина фиксируются отдельным commit.

Перед фризом Delivery выполняет:

```bash
python scripts/demo-seed/reset_demo.py
python scripts/demo-rehearsal.py --public-url https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com
```

В день демо выполняется только чтение `/health`, открытие Telegram-бота,
локального видео и dashboard. Новых deploy в день показа нет.
