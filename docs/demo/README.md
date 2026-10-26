# Delivery: Demo Day

| Критерий | Доказательство |
|---|---|
| Публичный прод на релизном теге | URL и неизменяемый `v0.5.2-demo` указывают на задеплоенный commit `af194ff`; `/health` проверяется rehearsal-скриптом |
| Демо-данные и сброс одной командой | `scripts/demo-seed/reset_demo.py`; повторный запуск проверяется тестом |
| Деградация и видео-бэкап | `scripts/demo-rehearsal.py`, `artifacts/demo/plan-b-rehearsal.json`, `demo-backup.mp4` |
| Фриз за сутки | `release-freeze.md` с временем, владельцем и запретом deploy |

Это Delivery-артефакты. Сценарий выступления, финальные слайды и публикация
внешней ссылки на видео принадлежат Product, а модельные кейсы — AI Engineer.
