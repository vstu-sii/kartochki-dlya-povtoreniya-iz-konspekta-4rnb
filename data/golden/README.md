# data/golden

Пустышка. В лабе 1 первые 10 примеров golden dataset лежат прямо в `docs/quality/golden-dataset-plan.md` таблицей, отдельный файл пока не заводим.

Когда примеров станет больше 10–15 и таблица в Markdown станет неудобной, переносим их сюда в CSV или JSONL. Каждая запись содержит шесть полей: `origin`, `source_pdf`, `fragment_text`, `expected_thesis`, `expected_question`, `expected_answer`. Столбец `#` из Markdown-таблицы служит только для нумерации и в файл датасета не переносится.
