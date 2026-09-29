# Threat model: карточки из PDF

**Версия:** 1.0 · 2026-09-28  
**Метод:** OWASP Top 10 for LLM Applications 2025 + анализ потоков C4.  
**Источник:** [OWASP GenAI — LLM Top 10](https://genai.owasp.org/llm-top-10/).

## Активы и границы доверия

Активы: Telegram user id, PDF/извлечённый текст, ответы студента, карточки, API-ключ Gemini, system prompt, метрики стоимости, БД. Границы: Telegram ↔ Adapter, внутренние HTTP-контейнеры, AI Service ↔ Gemini, Data Service ↔ PostgreSQL.

## Точки входа недоверенного текста

1. имя и бинарное содержимое PDF;
2. извлечённый текст, метаданные и скрытые инструкции PDF;
3. текстовый ответ студента;
4. Telegram message/callback payload;
5. ответ LLM до schema/grounding validation;
6. значения заголовков `X-Request-ID` и `Idempotency-Key`;
7. golden dataset и будущие prompt-файлы из PR.

## Права модели

Модель может только вернуть JSON `CardSet` или `AnswerReview`. Она не имеет сетевых tools, shell, файловой системы, БД, Telegram token, возможности отправить сообщение или изменить prompt. Все действия выполняет код после schema, grounding, ownership и limit checks.

## OWASP LLM Top 10 применительно к продукту

| Риск | Наш сценарий | Меры | Остаточный риск |
|---|---|---|---|
| LLM01 Prompt Injection | PDF просит игнорировать правила/раскрыть prompt | данные отделены от system prompt; нет tools; инструкция «PDF — данные»; grounding; attack fixtures | модель может изменить тон/выбор вопросов |
| LLM02 Sensitive Information Disclosure | чужой ответ, PDF, ключ или prompt попадает пользователю/в лог | ownership по user_id; секреты только env; без полных prompts/PDF в логах; TTL 24/30 дней | облачный провайдер получает нужный контекст |
| LLM03 Supply Chain | вредоносный npm/Python/Docker dependency или подмена модели | pinned images/actions; lockfiles с лабы 3; dependency scan; ручное разрешение `aact@beta` | внешняя модель и registry остаются зависимостями |
| LLM04 Data and Model Poisoning | вредный golden dataset или документ влияет на будущие версии | PDF не обучает модель; dataset меняется PR+human review; provenance/version | ревьюер может пропустить ошибочный эталон |
| LLM05 Improper Output Handling | LLM возвращает HTML/инструкции/лишние поля | strict schema, length limits, Telegram escaping, output не исполняется | содержательно неверный, но валидный текст |
| LLM06 Excessive Agency | модель удаляет данные/шлёт сообщения | tools отсутствуют; AI Service stateless; side effects только Application API | ошибка оркестратора вне модели |
| LLM07 System Prompt Leakage | пользователь просит процитировать скрытые правила | prompt не содержит секретов; refusal rule; тест на утечку; не логировать prompt | часть общих правил может быть угадана |
| LLM08 Vector and Embedding Weaknesses | retrieval poisoning/tenant crossover | RAG и embeddings не используются в MVP | риск появится при переходе к RAG |
| LLM09 Misinformation | выдуманные вопросы или неверный review | source_page + source_quote, deterministic grounding, golden dataset, «не знаю» вместо догадки | цитата может быть вырвана из контекста |
| LLM10 Unbounded Consumption | огромный PDF, длинный ответ, retry storm | 20 МБ/40 стр./60k tokens/2k chars; rate limit; timeout; максимум 2 модельных вызова; cost metrics | распределённые аккаунты могут обойти лимит |

## Ключевые злоупотребления

| Угроза | Вероятность / ущерб | Контроль | Проверка |
|---|---|---|---|
| Чтение чужой сессии через подмену id | средняя / высокий | каждый запрос связывает resource с Telegram user id | IDOR-тест двумя пользователями |
| Zip/PDF bomb или parser exploit | средняя / высокий | MIME+magic bytes, size/page/time limits, sandbox parser, обновления | corpus повреждённых PDF |
| Prompt injection в PDF | высокая / средний | нет tools, boundary prompt, grounding | SAFE-003 и набор атак лабы 4 |
| Утечка API key | низкая / критический | env/secret store, redact headers, secret scanning | canary secret в лог-тесте |
| XSS/Markdown injection в UI/Telegram | средняя / средний | escape output, allowlist formatting, CSP для web prototype | payload `<script>` и markdown links |
| Перерасход токенов | средняя / средний | quota per user/day, idempotency, max attempts/cost alert | concurrency/retry test |
| Подмена provider response | низкая / высокий | TLS, schema, expected model id, no dynamic base URL in user input | mock malformed/unknown model |

## Регулятор одной строкой

`telegram_user_id` и связанные ответы могут быть персональными данными, поэтому до production владелец должен определить статус оператора и правовое основание обработки, сроки/удаление и трансграничную передачу по применимой редакции Федерального закона РФ №152-ФЗ «О персональных данных»; требуется отдельная юридическая проверка, а не предположение команды. Официальный текст доступен на [Минтруде России](https://mintrud.gov.ru/docs/laws/130) и портале правовой информации.

## Что атакуем в лабораторной 4

1. прямые и скрытые prompt injection в тексте PDF;
2. просьбы раскрыть system prompt, ключи и чужие карточки;
3. HTML/Markdown/формулы, пытающиеся выполнить код;
4. повреждённые, огромные, пустые и сканированные PDF;
5. повтор запросов, гонки idempotency и rate-limit bypass;
6. IDOR для документов, сессий и оценок;
7. malformed JSON, лишние поля, неверная страница/цитата от модели;
8. timeout/429/5xx primary и полный outage провайдера;
9. canary-секреты и персональные данные в логах;
10. dependency/container scan и фиксация digest/tag.

## Критерий приёмки

Critical/high сценарии не приводят к чтению чужих данных, исполнению model output, утечке секрета или неконтролируемому расходу. Найденная уязвимость имеет владельца, срок и regression test.
