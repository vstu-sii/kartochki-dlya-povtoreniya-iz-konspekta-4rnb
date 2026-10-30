# Актуальный статус после командного Q&A — 30.10.2026

Команда подтвердила участие четырёх ролей и устную репетицию вопросов: [протокол Q&A](qa-rehearsal-2026-10-30.md). Выбор v0.5.10-demo-candidate подтверждён. Публичные API-атаки и показанные ручные Telegram/PDF-кейсы выполнены; результаты доступны в протоколах ниже. Прежние упоминания неподтверждённого Q&A, выбора тега и отсутствия ручного прогона относятся к истории.

Открыто: дата демо и объявление фриза Delivery, общий прогон выступления с таймером и командные действия по слайдам/Plan B. Известные ограничения качества и безопасности сохраняются.

<details>
<summary>Предыдущие протоколы и статусы (история; актуальный статус выше)</summary>

## Ручной Telegram-прогон: актуальный статус

30.10.2026 София предоставила скриншоты: обычный PDF создал карточки, PDF с инъекцией получил отказ; точная инъекция в ответе трижды получила отказ, после неё обычное сообщение обработано. [Протокол, тестовые PDF и скриншоты](telegram-redteam-2026-10-30.md). Ручная проверка этих входов выполнена; прежний пункт «ручной Telegram/PDF-прогон не выполнен» ниже больше не актуален. Все неизвестные варианты атак не объявляются проверенными.

Выбор v0.5.10-demo-candidate подтверждён пользователем в чате. Открыты дата/фриз Delivery и фактическая репетиция Q&A; участие в ней не приписывается.

## Актуализация 30.10.2026

Публичный HTTP-прогон выполнен: **16/16** (14 блокировок инъекций и 2 безопасных контроля), без подмены модельного транспорта. Все три DEMO-ATK прошли. [Запросы, ответы и health до/после](public-redteam-2026-10-30.json); [runner](../../tests/security/run_public_demo_attacks.py). Setup создал отдельные тестовые карточки и сессию в production; чужие данные не использовались. Q4-AUTH-01 в этот прогон не входит, поэтому результат не называется 17/17. Это публичный API для извлечённого PDF-текста и ответа студента, не загрузка бинарного PDF и не ручной Telegram-прогон. Блокировка до вызова модели является ожидаемой защитой, а не доказательством устойчивости самой LLM.

SHA health до/после совпал с тегом `v0.5.10-demo-candidate`: `a60eee706ad17238c11e0c79f53f026fd68bdf81`. [Release gates](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/40919274884) и [integrated quality](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/40919274836) — success на этом SHA по GitHub API. Повторять gates ради документальной правки не требуется.

Остаётся человеку/команде: подтвердить, что этот тег окончательно выбран для выступления, и фриз; провести ручной Telegram/PDF-прогон и репетицию Q&A с Софией. Автоматическая проверка не подтверждает участие в репетиции. Предыдущие статусы ниже — история до этой актуализации; пункты о неподтверждённых gates и отсутствии публичного API-прогона заменены результатами выше.

# Lab6 Quality: статус и зависимости — 29.10.2026

## Обновление Delivery: релизный кандидат

Тег `v0.5.10-demo-candidate` соответствует публичному SHA `a60eee706ad17238c11e0c79f53f026fd68bdf81`. На нём прошли [quality gates](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/40919274884), [сборка](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/40919274864) и [integrated quality](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/40919274836). Проверки используют детерминированный режим. Локальный набор проверок входов на этом SHA прошёл 17/17: [результат](lab6-tag-attack-a60eee7.json); модельный транспорт подменён. Командное подтверждение версии и публичная репетиция атак остаются открытыми.

Это сверка документов, не свидетельство новых тестовых прогонов или репетиций.

| Требование Quality | Статус | Доказательство / остаток |
|---|---|---|
| Факты evals, regression, security из Lab5 | Оформлено | [trust-block](trust-block.md), ссылки на CI и отчёты |
| Динамика за семестр графиком | Оформлено | Исторический deterministic-график с границами сравнения |
| Известные ограничения | Оформлено | Скорость, полезность, identity, PDF и область security |
| Опасные примеры Lab5 | Частично | [redteam-check](redteam-check.md), ID и сохранённые результаты; публичный повтор открыт |
| Gates на демо-теге, результат приложен | Открыто | Есть CI Lab5; окончательная версия демо и свежий финальный прогон не подтверждены |
| Шпаргалка Quality | Подготовлена | [qa](qa.md); участие Quality в репетиции не подтверждено |

## Зафиксированные материалы других ролей

Ссылки закреплены на просмотренных коммитах, чтобы изменения веток не подменяли доказательства. Материалы не копировались и не объявляются частью Quality-тега.

- AI: [протокол](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/blob/81a3f46f493090f5ed4d659dc772508e42e91a8e/docs/demo-run.md), [кейсы](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/blob/81a3f46f493090f5ed4d659dc772508e42e91a8e/docs/demo/ai-cases.md), [AI Plan B](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/blob/81a3f46f493090f5ed4d659dc772508e42e91a8e/docs/demo/plan-b.md).
- Product: [презентация](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/blob/0e0bb576ec4dfbfd3fd7d8b40e77682516fc8d79/docs/demo/presentation.pdf), [сценарий и Q&A](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/blob/0e0bb576ec4dfbfd3fd7d8b40e77682516fc8d79/docs/demo/scenario.md), [видео и происхождение](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/blob/0e0bb576ec4dfbfd3fd7d8b40e77682516fc8d79/docs/demo/video-link.md).
- Delivery: [фриз](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/blob/53f97328dcd0ce45e8fb072f730dc2c1c5534427/docs/demo/release-freeze.md), [Plan B](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/blob/53f97328dcd0ce45e8fb072f730dc2c1c5534427/docs/demo/plan-b.md), [сброс данных](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/blob/53f97328dcd0ce45e8fb072f730dc2c1c5534427/scripts/demo-seed/README.md).

## Что требует команды

1. Delivery + команда: назначить неизменяемый демо-тег, дату показа, подтвердить SHA прода и объявить фриз за сутки. Название candidate само по себе не запрещает назначить существующий тег.
2. Quality + Delivery: после назначения версии выполнить финальные gates на чистом checkout тега и сохранить JSON/логи/CI URL. Runner: `python tests/evals/run_release_evals.py --release-ref <tag>`; результат по умолчанию artifacts/evals/lab5-release-results.json. Не использовать WORKTREE как сертификат релиза.
3. Quality + Delivery + AI: проверить инъекции на настоящем демо-вводе с разрешёнными тестовыми данными; приложить протокол. Текущие 17/17 этого не заменяют.
4. Product + все роли: провести полный живой прогон и Q&A с Quality. Первый кабинетный прогон 11:33, второй 9:11: «уложились дважды» пока не доказано. Исправить 9:15 в чеклисте Product на согласованный фактический результат.
5. AI + Delivery + Product: согласовать пороги 12/30 секунд и один Plan B, объединить AI-раздел и инфраструктурный раздел без потери файлов. Проверить воспроизведение видео и мобильный канал лично.
6. Product: перенести актуальный trust-block и ограничения на слайды; Quality должна сверить финальный PDF после обновления.
7. Все роли: согласовать общую базу сдачи либо ссылки между PR. У каждой роли материалы в отдельной ветке; их наличие у команды не означает наличие в Quality checkout.

## Выполнено этой правкой

Добавлены график и источники, свежие метрики AI с границами сравнения, существенные ограничения, таблица соответствия атак Lab5, пояснение пути JSON, ссылки на командные коммиты и статусы зависимостей. Исторические результаты не изменялись. Новые успехи тестов, фриз и человеческие подтверждения не приписывались.

</details>
