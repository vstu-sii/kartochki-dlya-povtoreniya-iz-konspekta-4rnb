# Карточки для устной защиты лабы

## Что это

Telegram-бот: студент загружает PDF методички по одной лабораторной, получает 5–10 вопросов с опорой на источник, отвечает текстом и получает разбор. Готовимся к устной защите одной лабораторной, не ко всему экзамену. Формат входа в MVP — только PDF с текстовым слоем.

Подробности сегмента и боли: `docs/prd.md`.

## Команда и роли

| Роль | Кто | Зона ответственности |
|---|---|---|
| Product / VO | Доброквашина Анастасия | use cases, roadmap, глоссарий, приёмка ADR |
| AI Engineer | Цвилева Вероника | AI-пайплайн, выбор модели, спайки, OpenAPI AI |
| Delivery | Ермакова Алиса | C4, aact, прототип UI, схема БД, compose |
| Quality & Safety | Ткаченко София | DoD, golden dataset, тест-план, threat model |

## Структура репозитория (лабораторная 2)

```
СИИ/
├── README.md
├── aact.config.ts
├── compose.dev.yml
├── api/openapi.yaml
├── database/schema.sql
├── docs/
│   ├── use-cases/           Product
│   ├── roadmap.md           Product
│   ├── glossary.md          Product
│   ├── adr/                 Product + Delivery
│   ├── ai-pipeline.md       AI Engineer
│   ├── model-candidates.md  AI Engineer
│   ├── experiments/lab2.md  AI Engineer
│   ├── architecture/        Delivery
│   └── quality/             Quality & Safety
├── notebooks/lab2_spikes.ipynb
├── frontend/prototype/
├── backend/                 health-заглушки compose
├── ml/                      health-заглушка AI Service
└── tests/test_lab2*.py
```

## Лабораторная 2 — проектирование системы

**Product:** `docs/use-cases/`, `docs/roadmap.md`, `docs/glossary.md`, `docs/adr/`.

**AI Engineer:** `docs/ai-pipeline.md`, решение в `docs/model-candidates.md`, `docs/experiments/lab2.md`, `notebooks/lab2_spikes.ipynb`, `api/openapi.yaml`.

**Delivery:** `docs/architecture/`, `aact.config.ts`, `frontend/prototype/`, `database/schema.sql`, `compose.dev.yml`.

**Quality & Safety:** `docs/quality/dod.md`, `docs/quality/golden-dataset/`, `docs/quality/test-plan.md`, `docs/quality/threat-model.md`.

Проверка комплектности:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Ручные артефакты закрыты: `docs/use-cases/validation.md`, `docs/team-sync-lab2.md`, `docs/architecture/aact-check.md` (**0 violations**), `docs/architecture/compose-verify.md`.

## Как поднять окружение локально

1. Склонировать репозиторий.
2. Скопировать `.env.example` в `.env` (для health-скелета LLM-ключ не обязателен).
3. Запустить Docker Desktop.
4. Выполнить:

```bash
docker compose -f compose.dev.yml up --build
```

UI-прототип: `http://localhost:8080`. Остальные сервисы — внутри сетей compose, проверяются health checks.

## Прод

Прод URL: https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com

Сейчас размещён hello-world из лабораторной 1; в лабораторной 3 Delivery заменит его приложением бота по `docs/deploy.md`.

## Ветки и PR (лабораторная 2)

Каждая роль сдаёт отдельный PR из ветки `lab2-[role]-design`.

| Роль | Ветка | Заголовок PR |
|---|---|---|
| Product / VO | `lab2-product-design` | `Lab2: Product — Design Deliverables` |
| AI Engineer | `lab2-ai-design` | `Lab2: AI Engineer — Design Deliverables` |
| Delivery | `lab2-delivery-design` | `Lab2: Delivery — Design Deliverables` |
| Quality & Safety | `lab2-quality-design` | `Lab2: Quality — Design Deliverables` |

Шаблон PR: `.github/PULL_REQUEST_TEMPLATE.md`.
