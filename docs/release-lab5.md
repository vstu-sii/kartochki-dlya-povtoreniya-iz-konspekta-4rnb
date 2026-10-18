# Воспроизводимый релиз Lab 5

- прямые runtime-зависимости закреплены в `requirements.lock`;
- `.github/workflows/release.yml` на теге `v*` запускает тесты, проверяет и собирает Compose;
- `scripts/build_release_manifest.py` сохраняет commit и SHA-256 входов сборки;
- workflow публикует `lab5-release-<tag>`.

Релиз собирается только из общего интеграционного коммита, содержащего изменения всех четырёх ролей. Сначала создаётся RC-тег `v0.5.0-rc1`; оба tag-workflow должны стать зелёными. После этого тот же проверенный коммит получает финальный тег `v0.5.0`. Manifest генерируется внутри CI и содержит точный commit и SHA-256 входов сборки; он не хранится в ветке как устаревающий файл.

## Фактический релиз

Тег `v0.5.0` создан на общем коммите `213ed28`. GitHub Actions подтвердил:

- [Lab5 reproducible release — success](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/39175400922): зависимости, тесты, Compose config/build и manifest;
- [Lab5 release quality gates — success](https://github.com/vstu-sii/kartochki-dlya-povtoreniya-iz-konspekta-4rnb/actions/runs/39175400930): полный eval/security/integration gate.

RC1 обнаружил shallow-checkout в security-before; RC2 после `fetch-depth: 0` прошёл, после чего финальный тег запущен на том же исправленном коммите. Тег не перемещался.
