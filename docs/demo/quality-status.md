# Lab6 Quality: статус и зависимости — 29.10.2026

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
