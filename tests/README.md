# tests

В лабораторной 2 dependency-free тесты проверяют комплектность, воспроизводимость notebook, архитектурные границы, число и формат golden cases, SQL/compose и наличие скриншота.

```bash
python -m unittest discover -s tests -p "test_lab2*.py" -v
```

С лабораторной 3 добавляются unit/contract/integration tests и mini-eval реального pipeline.
