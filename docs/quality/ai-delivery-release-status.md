# Статус совместных пунктов AI + Delivery

**Проверено:** 27.10.2026  
**AI-ветка:** `lab5-ai-testing`  
**Проверенная вершина AI до добавления этого отчёта:** `9d29cf2e7ebd922f720c318691d3ee4e05f49a3b`

Сырые проверенные факты сохранены в `artifacts/ai/production-delivery-verification-2026-10-27.json`.

## Что подтверждено

- Production `https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com/health` отвечает `status=ok`, версия сервиса `lab5`.
- OpenAPI production сообщает версию API `0.5.0`.
- Тег Delivery `v0.5.2-demo` указывает на `af194ff1b5823afe17ad1508ef1ef1a92fbdfef5`.
- GitHub Actions run `40419542561` завершён успешно на `v0.5.2-demo`; артефакт `lab5-release-v0.5.2-demo` существует и не истёк.
- Delivery/Plan B run `40419517004` завершён успешно на `c7c6485afc2f1d9d31bfe0e5f0dd59926bcfd2fd`; артефакт `lab6-delivery-plan-b` существует и не истёк.
- Последний полный quality run `39221429651` завершён успешно на старом теге `v0.5.1`; артефакт `lab5-quality-v0.5.1` существует и не истёк.
- Критерий потери формул закрыт на AI-ветке: 39/39 формул сохранены, потеря `0/39 = 0% < 10%`. Доказательства: `artifacts/ai/formula-fix-2026-10-27/`.

## Контрольный production-запрос

Один запрос создания пяти карточек выполнен через публичный API. Получено:

| Поле | Значение |
|---|---:|
| `model` | `deterministic-grounded-v1` |
| `fallback_used` | `true` |
| `latency_ms` | `31859` |
| `usage.input_tokens` | `205` |
| `usage.output_tokens` | `515` |
| карточек | `5` |

Production и fallback работоспособны, но этот результат **не является Gemini-прогоном**. Delivery отдельно зафиксировал причиной своего предыдущего fallback `gemini_http_503`. Токены fallback нельзя использовать для расчёта фактической стоимости Gemini.

## Что ещё не закрыто

1. В Render требуется настроить доступную Gemini-модель и выполнить Manual Deploy. Успешный ответ должен одновременно содержать имя Gemini, `fallback_used=false`, `fallback_reason=null`, `trace_id`, фактический `usage` и карточки.
2. После успешного сценария `1 генерация + 5 разборов` AI суммирует фактические provider-токены, применяет тариф модели и сравнивает стоимость с бюджетом Lab1 `$0.04` за сессию.
3. `v0.5.2-demo` не содержит актуальную AI-вершину. После интеграции AI, Delivery и Quality нужен новый общий SHA и новый неизменяемый тег.
4. Release workflow и полный quality workflow должны быть зелёными именно на новом теге; их ссылки и артефакты затем добавляются в этот отчёт.

До выполнения этих условий нельзя отмечать «успешный Gemini без fallback» и «финальный общий релиз» как завершённые.

## Исправление AI после production-проверки

При независимой проверке Gemini начал отвечать без fallback, но запрос пяти карточек нестабильно возвращал четыре, а генерация не содержала `trace_id`. Исправления подготовлены в AI SHA `d27ae19edb3a87fd11fc5b9e0a44b7b4cc393510`:

- generation contract требует ровно `requested_card_count`;
- prompt повышен до `cards-v2.2`;
- модельный `trace_id` сохраняется и возвращается также при idempotent replay;
- полный локальный gate: 8/8 групп, 132/132 кейса, 48/48 unit/integration.

Подробности: `artifacts/ai/gemini-contract-fix-2026-10-27/README.md`. До интеграции этого SHA и нового production deploy текущий релизный кандидат не подтверждает исправленный контракт.
