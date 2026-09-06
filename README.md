# Карточки для устной защиты лабы

## Что это

Телеграм бот, которому скидываешь PDF методички или конспект лекции по своей лабораторной работе. Бот вытаскивает из него 5-10 ключевых тезисов и превращает их в вопросы. Дальше ты отвечаешь текстом, а бот сверяет твой ответ с ключевыми моментами и говорит, где ты не прав.

Готовимся не ко всему экзамену, а конкретно к устной защите теоретической части одной лабораторной работы. Формат входа на первой итерации только PDF.

Подробно про сегмент, боли и цель продукта смотри в `docs/prd.md`.

## Команда и роли

| Роль | Кто | Зона ответственности |
|---|---|---|
| Product / VO | Доброквашина Анастасия | сегмент, боли, гипотезы, глоссарий, бриф |
| AI Engineer | Цвилева Вероника | ресёрч, выбор модели, первые эксперименты с промптами |
| Delivery | Ермакова Алиса | репозиторий, окружение, CI, деплой |
| Quality & Safety | Ткаченко София | метрики качества, golden dataset, DoD |


## Структура репозитория

Один репозиторий на всех. Структура здесь сразу заложена под лабу 3, часть папок в лабе 1 это пустышки с пояснением, чтобы потом догрузить.

```
СИИ/
├── README.md                 Delivery
├── .gitignore                 Delivery
├── .env.example                Delivery
├── compose.dev.yml            Delivery
├── Dockerfile                  Delivery
├── .github/
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/ci.yml
├── docs/                      документы всех ролей, разные файлы
│   ├── prd.md                 Product
│   ├── hypotheses.md          Product
│   ├── insights.md            Product (бонусный шаг, пока заглушка)
│   ├── glossary.md            Product
│   ├── brief.md                Product
│   ├── research.md            AI Engineer
│   ├── model-candidates.md    AI Engineer
│   ├── deploy.md               Delivery
│   ├── experiments/lab1.md    AI Engineer
│   └── quality/
│       ├── success-criteria.md      Quality
│       ├── golden-dataset-plan.md   Quality
│       └── dod-draft.md             Quality
├── notebooks/                 AI Engineer, пробы промптов
│   └── lab1_experiments.ipynb
├── backend/                   заглушка сейчас, API появится в лабе 2-3
├── frontend/                  пустышка до лабы 3
├── ml/                        пустышка до лабы 3
├── tests/                     пустышка, evals с лабы 3
└── data/golden/               эталоны, в лабе 1 только примеры в docs/quality
```


## Как поднять окружение локально

1. Склонировать репозиторий
2. Скопировать `.env.example` в `.env` и заполнить своими ключами
3. Выполнить:

```bash
docker compose -f compose.dev.yml up --build
```


## Прод

Прод URL: https://kartochki-dlya-povtoreniya-iz-konspekta.onrender.com

Заглушка hello-world, задеплоено по инструкции из `docs/deploy.md`. Delivery вписывает сюда реальную ссылку сразу после деплоя.

## Ветки и PR

Каждая роль сдаёт лабу отдельным PR из ветки `lab1-[role]-initiation`, например `lab1-product-initiation`. Заголовок PR: `Lab1: [Role] — Initiation Deliverables`. Шаблон PR лежит в `.github/PULL_REQUEST_TEMPLATE.md`.
