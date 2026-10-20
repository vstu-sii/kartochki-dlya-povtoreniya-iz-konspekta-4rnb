# Внешний прогон UC для Lab 5 / North Star

**Проверяющий:** Постернак Денис — студент другой команды курса, не участник проекта.  
**Наблюдатель:** Доброквашина Анастасия (Product).  
**Среда:** живой Telegram-бот на публичном контуре (тот же продукт, что готовится к релизу `v0.5.1`).  
**Материал:** PDF методички Linux / гипервизор с текстовым слоем.

## Две связанные сессии

### A. Ручной внешний прогон — 15.10.2026, 20:55–21:08

Источник кадров: `docs/quality/evidence/2026-10-15/` (извлечены из «проверки как просил.docx»). Полная таблица UC: `validation-lab3.md` (имя и протокол Дениса).

| Шаг | Факт | Свидетельство |
|---|---|---|
| UC-01 | Создан набор **из 5 карточек**; видны вопросы и цитаты | [1](../quality/evidence/2026-10-15/uc-evidence-1.png), [2](../quality/evidence/2026-10-15/uc-evidence-2.png), [5](../quality/evidence/2026-10-15/uc-evidence-5.png) |
| UC-02 | Верный ответ принят, «о цветах» отклонён | [1](../quality/evidence/2026-10-15/uc-evidence-1.png), [2](../quality/evidence/2026-10-15/uc-evidence-2.png) |
| UC-03 | «Полезно» → «Не полезно» подтверждены | [3](../quality/evidence/2026-10-15/uc-evidence-3.png), [4](../quality/evidence/2026-10-15/uc-evidence-4.png) |
| UC-04 | `/start` вернул карточку 3 | [5](../quality/evidence/2026-10-15/uc-evidence-5.png) |
| UC-05 | PNG отклонён | [6](../quality/evidence/2026-10-15/uc-evidence-6.png) |
| North Star | Денис без подсказок завершил **5 карточек** в одной начатой сессии | серверная сессия backend (`study_sessions`, `current_position >= 5`); протокол наблюдателя Product |

Вопросов к наблюдателю: 0. Критических остановок: 0.

Как сессия пишется на сервере: Telegram-бот создаёт `StudySession` через `POST /v1/ai/sessions`, каждое продвижение — `PATCH /sessions/{id}/progress`, resume читает позицию из БД. Поэтому завершение пяти карточек Денисом — та же серверная запись `current_position = 5`, которую считает формула PRD. На скриншотах видны карточки 1–3; завершение набора наблюдатель зафиксировал в той же непрерывной сессии. Экспорт записи для воспроизводимого расчёта: `artifacts/product/north-star-sessions-export.json`; расчёт: `scripts/measure_north_star.py`.

### B. Публичный API-прогон на проде — 19.10.2026

Машиночитаемое свидетельство: `artifacts/product/lab5-prod-uc.json`.

| UC | Результат |
|---|---|
| UC-01 | HTTP 201, `card_count: 5` |
| UC-02 | review `correct` |
| UC-03 | rating 200 |
| UC-04 | `persist_progress` position **5**, resume 200 |
| UC-05 | 422 `PROMPT_INJECTION_BLOCKED` |

Этот прогон подтверждает, что на публичном URL путь «5 карточек → position ≥ 5» технически воспроизводится. **В North Star не входит:** пользователь `lab5-external-smoke-*` — служебный smoke, не внешний студент.

### C. UC-06 / UC-07 на теге `v0.5.1`

Проверены integration gate релиза (не destructive canary на пользовательской квоте). Ссылка: [quality gate run](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/39221429651). В знаменатель North Star не входят.

## Итог для Lab 5 Product

- Ручная приёмка UC внешним человеком: **пройдена** (Денис, 15.10.2026).  
- North Star: **1/1** внешних сессий достигли ≥5 карточек; n=1 → цель 70% формально достигнута, статистически не подтверждена до n≥10.  
- Прод-путь UC-01…05: подтверждён `lab5-prod-uc.json` 19.10.2026.
