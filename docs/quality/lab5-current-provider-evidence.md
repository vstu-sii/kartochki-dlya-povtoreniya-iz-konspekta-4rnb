# Lab5: проверка Gemini и релиза

Релизный кандидат `v0.5.8-integrated-candidate` указывает на `5504ef5d73ec2c6b1a5fedb7e675737e32df4135`. Публичный `/health` при замере подтвердил этот SHA. Результаты записаны после создания тега и не входят в его дерево.

- [Воспроизводимая сборка](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/40573059216): success.
- [Release quality gates](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/40573059363): success; автоматический набор использует детерминированный режим и не является замером качества Gemini.
- [Integrated release quality](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/40573059355): success.

27 октября 2026 UTC выполнены три сценария на проде с `gemini-3.5-flash-lite`: обычные PDF и PDF с формулами, генерация и пять ответов на сценарий. Все вызовы завершились без fallback, карточки открылись повторно. [Сырые результаты](../../artifacts/quality/lab5-production-final/gemini-series-5504.json): p95 генерации 8,028 с (3 запроса), p95 разбора 23,807 с (15 запросов), метод nearest-rank; целевой порог 7 с для разбора в этом прогоне не достигнут. Выборка мала для устойчивых выводов об SLA. Расчётная стоимость трёх сценариев по указанному в JSON тарифу — $0,0110711; это оценка, не счёт провайдера.

[Дополнительный сценарий с формулами](../../artifacts/quality/lab5-production-final/gemini-diagnostic-5504.json) прошёл без fallback; p95 пяти разборов 5,373 с. При проверке использовались ответы, сформированные из эталона карточки; это не независимая оценка способности распознавать пересказ своими словами. Для подтверждения качества живой модели нужен отдельный прогон размеченного golden dataset. История неудачных проверок сохраняется как доказательство ограничений.
