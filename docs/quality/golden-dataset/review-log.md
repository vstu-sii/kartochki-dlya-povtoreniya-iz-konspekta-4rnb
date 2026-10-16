# Подтверждение новых эталонов golden dataset v2

15.10.2026 получено подтверждение команды: все восемь новых эталонов совместно проверены и согласованы, аудит состоялся. Ниже сохранены назначенные ответственные пары. Отдельная дата каждой проверки и индивидуальные подписи не переданы; дата в таблице — дата получения общего подтверждения.

Скриншоты методички Linux подтверждают ручные пользовательские сценарии, но не являются изображениями выполнения этих восьми golden-кейсов. Основание approved — явное подтверждение команды о ревью эталонов. Автоматические результаты имеют отдельные источники.

| Кейс | Проверяющие | Источник автоматического результата | Ручной статус |
|---|---|---|---|
| GEN-LIVE-001 | Ткаченко София, Цвилева Вероника | [результат](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/blob/93036ccf67d6321857fab0ff10b7d19f6560d681/artifacts/evals/baseline-results.json#case=GEN-LIVE-001) | approved; подтверждение команды 15.10.2026 |
| GEN-LIVE-002 | Ткаченко София, Цвилева Вероника | [результат](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/blob/93036ccf67d6321857fab0ff10b7d19f6560d681/artifacts/evals/baseline-results.json#case=GEN-LIVE-002) | approved; подтверждение команды 15.10.2026 |
| REV-LIVE-001 | Ткаченко София, Цвилева Вероника | [результат](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/blob/93036ccf67d6321857fab0ff10b7d19f6560d681/artifacts/evals/baseline-results.json#case=REV-LIVE-001) | approved; подтверждение команды 15.10.2026 |
| REV-LIVE-002 | Ткаченко София, Цвилева Вероника | [результат](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/blob/93036ccf67d6321857fab0ff10b7d19f6560d681/artifacts/evals/baseline-results.json#case=REV-LIVE-002) | approved; подтверждение команды 15.10.2026 |
| SAFE-LIVE-001 | Ткаченко София, Ермакова Алиса | [результат](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/blob/38bc5746a7e10d0d15d79027b6692cf520856b79/artifacts/evals/application-results.json#case=SAFE-LIVE-001) | approved; подтверждение команды 15.10.2026 |
| SAFE-LIVE-002 | Ткаченко София, Ермакова Алиса | [результат](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/blob/38bc5746a7e10d0d15d79027b6692cf520856b79/artifacts/evals/application-results.json#case=SAFE-LIVE-002) | approved; подтверждение команды 15.10.2026 |
| STATE-LIVE-001 | Ткаченко София, Ермакова Алиса | [результат](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/blob/38bc5746a7e10d0d15d79027b6692cf520856b79/artifacts/evals/application-results.json#case=STATE-LIVE-001) | approved; подтверждение команды 15.10.2026 |
| UX-LIVE-001 | Ткаченко София, Ермакова Алиса | [результат](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/blob/38bc5746a7e10d0d15d79027b6692cf520856b79/artifacts/evals/application-results.json#case=UX-LIVE-001) | approved; подтверждение команды 15.10.2026 |

[Протокол получения свидетельств и подтверждения](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/blob/lab3-product-prototype/docs/quality/evidence/2026-10-15/README.md). Исходные input/context/expected_output не изменены. Для SAFE/STATE/UX источник исправлен на application-results.json: в модельном отчёте эти кейсы пропущены.

## Дополнения Lab4 — статус 16.10.2026

SEC-L4-001, SEC-L4-002, BUDGET-L4-001, TOOL-L4-001: **pending human review**.
В прежних строках стояло team-confirmed без имён/даты/основания; это исправлено на pending.
Подтверждение восьми Lab3 кейсов выше не распространяется на эти четыре.
Технические прогоны выполнены и сохранены отдельно; они не заменяют человеческое ревью.
Для закрытия нужны реальные проверяющие, дата и результат проверки каждого эталона.
