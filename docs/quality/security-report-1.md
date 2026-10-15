# Security report v1 — атаки до исправлений

Команда:

```bash
python tests/security/run_attacks.py --mode before --output artifacts/security/lab4-attacks-before.json
```

Набор содержит прямые и обходные prompt injection для PDF, ответа студента и псевдо-тегов model/tool, плюс два безопасных контрольных текста. Guard лабораторной 3 проверял размер, MIME и grounding, но не содержание injection.

## Найденные дыры

| Класс | Результат до | Риск | Задача |
|---|---|---|---|
| Ignore previous/system instructions | пропускался | P0: изменение поведения reviewer/generator | `SEC-01`, Quality + Delivery |
| Запрос раскрыть system prompt | пропускался | P0: утечка внутренних инструкций | `SEC-02`, Quality + AI |
| HTML-like system/tool tags | пропускались | P0: попытка вызвать несуществующее необратимое действие | `SEC-03`, Delivery |
| Пунктуация и zero-width обход | пропускался | P1: обход точного regex | `SEC-04`, Quality |

Источник истины — `artifacts/security/lab4-attacks-before.json`. Это воспроизводимый результат старой политики, а не список разовых ручных промптов.
