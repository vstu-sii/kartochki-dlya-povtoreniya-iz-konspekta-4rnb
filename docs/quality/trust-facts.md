# Факты доверия для Demo Day

## Что доказано

- 132/132 golden-кейса исполнены полным runner без waiver.
- Schema, grounding и safety — 100%; после Lab5 review agreement — 92,86% при пороге 85%.
- 37/37 application/API/DB сценариев зелёные.
- 17/17 повторных атак после исправлений заблокированы, включая три сценария Demo Day.
- Retrieval hit@1 и recall@3 — 100% на текущем наборе.
- Реальный Gemini prompt-only A/B: B 100%, A 95% на 20 кейсах; модель `gemini-3.5-flash-lite`.

## Чего мы не утверждаем

- Локальные 2–3 мс разных deterministic-runner не являются latency Gemini; финальный model runner имеет p95 3 мс.
- 20 provider-кейсов не доказывают качество на всём домене.
- 100% на golden dataset не означает отсутствие атак вне набора.
- North Star 1/1 не является устойчивой пользовательской статистикой.
- Результат относится только к неизменяемому тегу `v0.5.0`; последующие изменения веток требуют нового тега и повторного gate.

## Воспроизведение

Локально: `python tests/evals/run_release_evals.py --release-ref WORKTREE`. На теге CI вызывает ту же команду с именем тега и сохраняет все JSON/логи даже при ошибке.

Фактическое подтверждение тега `v0.5.0`: [quality gate](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/39175400930) и [release build](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/39175400922) завершились `success`.
