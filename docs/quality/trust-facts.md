# Факты доверия для Demo Day

## Что доказано

- 132/132 golden-кейса исполнены полным runner без waiver.
- Schema, grounding и safety — 100%; после Lab5 review agreement — 92,86% при пороге 85%.
- 37/37 application/API/DB сценариев зелёные; retrieval hit@1 и recall@3 — 100% на текущем наборе.
- 17/17 security-проверок прошли: 14 инъекций заблокированы (включая три Demo Day-сценария), два безопасных запроса разрешены, анонимный запрос отклонён без раскрытия карточек.
- Реальный Gemini prompt-only A/B: B 100%, A 95% на 20 кейсах; модель `gemini-3.5-flash-lite`.

## Чего мы не утверждаем

- Локальные 2–3 мс разных deterministic-runner не являются latency Gemini; финальный model runner имеет p95 3 мс.
- 20 provider-кейсов не доказывают качество на всём домене.
- 100% на golden dataset не означает отсутствие атак вне набора.
- North Star 1/1 не является устойчивой пользовательской статистикой.
- Результат относится только к неизменяемому тегу `v0.5.1`; последующие изменения веток требуют нового тега и повторного gate.

## Воспроизведение

Локально: `python tests/evals/run_release_evals.py --release-ref WORKTREE`. На теге CI вызывает ту же команду с именем тега и сохраняет все JSON/логи даже при ошибке.

Фактическое подтверждение тега `v0.5.1`: [quality gate](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/39221429651) и [release build](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/39221429842) завершились `success`.

## Скриншоты для презентации — пока не приложены

Пункт остаётся открытым до получения двух реальных снимков: дашборда с данными и успешного release quality gate. [Инструкция и подписи](evidence/lab5/README.md). Старые скриншоты Lab3 не подтверждают Lab5. Нельзя подменять отсутствие снимков ссылкой на конфигурацию Grafana.

Provider A/B: [результат на v0.5.1](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/blob/v0.5.1/artifacts/experiments/lab4-provider-results.json).
