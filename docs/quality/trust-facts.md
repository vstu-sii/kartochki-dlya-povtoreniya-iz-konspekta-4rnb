# Факты доверия для Demo Day

## Что доказано

- 132/132 golden-кейса исполнены полным runner без waiver.
- Schema, grounding и safety — 100%; review agreement — 90,48% при пороге 85%.
- 37/37 application/API/DB сценариев зелёные.
- 14/14 повторных атак после исправлений заблокированы.
- Retrieval hit@1 и recall@3 — 100% на текущем наборе.
- Реальный Gemini prompt-only A/B: B 100%, A 95% на 20 кейсах; модель `gemini-3.5-flash-lite`.

## Чего мы не утверждаем

- Локальные 2 мс не являются latency Gemini.
- 20 provider-кейсов не доказывают качество на всём домене.
- 100% на golden dataset не означает отсутствие атак вне набора.
- North Star 1/1 не является устойчивой пользовательской статистикой.
- Пока запрещены коммит/тег, результат имеет статус release candidate, не финального tagged release.

## Воспроизведение

`python tests/evals/run_release_evals.py --release-ref WORKTREE`. После создания тега CI вызывает ту же команду с именем тега и сохраняет все JSON/логи даже при ошибке.
