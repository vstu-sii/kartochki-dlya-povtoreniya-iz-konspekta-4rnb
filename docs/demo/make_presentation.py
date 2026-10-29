from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import simpleSplit
from pathlib import Path

pdfmetrics.registerFont(TTFont("Arial", "C:/Windows/Fonts/arial.ttf"))
pdfmetrics.registerFont(TTFont("ArialBold", "C:/Windows/Fonts/arialbd.ttf"))

# One slide = one thought. 12 slides: pain, solution, numbers, team, AI, trust.
slides = [
    {
        "kicker": "DEMO DAY  ·  ЛАБОРАТОРНАЯ 6",
        "title": "Из длинного PDF — к устной защите",
        "lines": [
            "Карточки для повторения из конспекта",
            "10 минут: боль → живое демо с прода → цифры",
        ],
    },
    {
        "kicker": "БОЛЬ",
        "title": "Методичку трудно превратить в проверку себя",
        "lines": [
            "Долго вручную делать вопросы по PDF.",
            "Нельзя проверить ответ своими словами.",
            "Неясно, откуда взята «правильная» формулировка.",
            "Прогресс между заходами теряется.",
        ],
    },
    {
        "kicker": "РЕШЕНИЕ",
        "title": "Telegram-бот: PDF → 5 grounded-карточек",
        "lines": [
            "Загружаете один конспект.",
            "Получаете вопросы со страницей и дословной цитатой.",
            "Отвечаете своими словами — видите разбор, не шпаргалку.",
            "Сессия сохраняется: можно продолжить с того же места.",
        ],
    },
    {
        "kicker": "ЧТО ПОКАЗЫВАЕМ",
        "title": "Один путь пользователя, не архитектура",
        "lines": [
            "UC-01  загрузить PDF → 5 карточек",
            "UC-02  ответить своими словами → вердикт и пробелы",
            "Цитата на карточке — из загруженного файла, не «из модели»",
            "Прод: kartochki-dlya-povtoreniya-iz-konspekta.onrender.com",
        ],
    },
    {
        "kicker": "КАК РАБОТАЕТ AI",
        "title": "Модель предлагает, приложение проверяет",
        "lines": [
            "PDF → текст и страницы → фрагменты → Gemini (JSON Schema)",
            "Контроль: ровно 5 карточек и цитата есть в источнике",
            "Разбор ответа: verdict + feedback + missing points",
            "Отказ провайдера → локальный fallback, сессия цела",
        ],
    },
    {
        "kicker": "ЦИФРЫ AI ЗА СЕМЕСТР",
        "title": "Не прилагательные — измеренные пороги",
        "lines": [
            "Schema / grounding: 100% / 100% на golden",
            "Review: Lab3 90,48% → Lab5 ablation 92,86% (порог ≥85%)",
            "Сырой lexical overlap — 71,43%; aliases+contradiction держат качество",
            "Gemini A/B prompt B: 100% vs 95% на 20 кейсах",
        ],
    },
    {
        "kicker": "ПОЧЕМУ НАМ МОЖНО ВЕРИТЬ",
        "title": "Gates зелёные, атаки прогнаны, ограничения названы",
        "lines": [
            "132/132 golden · 37/37 application",
            "17/17 security-проверок: 14 block + 2 allow + 1 auth deny",
            "Не «все заблокированы»: два сценария обязаны пропускать учебный текст",
            "Релиз-кандидат: v0.5.9-integrated-candidate, SHA в /health",
        ],
    },
    {
        "kicker": "NORTH STAR",
        "title": "Доля сессий, дошедших до 5 карточек",
        "lines": [
            "Цель PRD: ≥70% внешних сессий с current_position ≥ 5",
            "Факт: 1/1 = 100% (Постернак Денис, 15.10.2026)",
            "Замер: study_sessions, не «со слов команды»",
            "Честно: n=1. Для устойчивого вывода нужно ≥10 внешних сессий",
        ],
    },
    {
        "kicker": "КОМАНДА",
        "title": "Кто говорит и за что отвечает",
        "lines": [
            "Product / VO — Доброквашина Анастасия: история, тайминг, North Star",
            "Delivery — Ермакова Алиса: прод, Telegram, Plan B",
            "AI — Цвилева Вероника: пайплайн, кейсы, fallback",
            "Quality — Ткаченко София: evals, security, ограничения",
        ],
    },
    {
        "kicker": "ОГРАНИЧЕНИЯ",
        "title": "Называем сами — до вопроса из зала",
        "lines": [
            "Один PDF за раз; рукопись и плохой скан — вне обещания",
            "Цитата проверяется, истинность исходного PDF — нет",
            "X-User-ID — не полноценная аутентификация",
            "Латентность Gemini нестабильна: на репетиции p95 до ~20 с",
        ],
    },
    {
        "kicker": "PLAN B",
        "title": "Если прод или модель не успевают",
        "lines": [
            "Live >12 с на карточку → кэш кейса, прямо говорим «бэкап»",
            "Нет сети / Render → видео 2:10 с прода (telegram-promo.mp4)",
            "Отказ Gemini → grounded fallback, не пустой экран",
            "Мобильный интернет — запасной канал Delivery",
        ],
    },
    {
        "kicker": "ЧТО ДАЛЬШЕ",
        "title": "Концепция измерена. Следующий риск — выборка",
        "lines": [
            "P0: ≥10 внешних сессий, цель ≥7/10 до пяти карточек",
            "P1: повтор Gemini A/B и OCR сложных сканов",
            "Не скрываем: ценность на n=1 ещё не статистика",
            "Вопросы?",
        ],
    },
]

path = Path(__file__).with_name("presentation.pdf")
c = canvas.Canvas(str(path), pagesize=(960, 540))
bg = HexColor("#101c34")
accent = HexColor("#52e2c2")
white = HexColor("#ffffff")
body = HexColor("#d6e2f5")
mute = HexColor("#8ea6c8")

for i, slide in enumerate(slides, 1):
    c.setFillColor(bg)
    c.rect(0, 0, 960, 540, fill=1, stroke=0)
    c.setFillColor(accent)
    c.rect(0, 0, 8, 540, fill=1, stroke=0)
    c.setFont("Arial", 13)
    c.drawString(48, 492, slide["kicker"])
    c.setFillColor(white)
    c.setFont("ArialBold", 28)
    title_lines = simpleSplit(slide["title"], "ArialBold", 28, 860)
    y = 430
    for line in title_lines:
        c.drawString(48, y, line)
        y -= 34
    y -= 12
    c.setFillColor(body)
    c.setFont("Arial", 18)
    for item in slide["lines"]:
        wrapped = simpleSplit("•  " + item, "Arial", 18, 850)
        for j, line in enumerate(wrapped):
            c.drawString(48 if j == 0 else 72, y, line)
            y -= 28
        y -= 8
    c.setFillColor(mute)
    c.setFont("Arial", 12)
    c.drawString(48, 28, f"{i:02}  /  {len(slides):02}")
    c.drawRightString(912, 28, "карточки из конспекта")
    c.showPage()

c.save()
print(f"wrote {path} ({len(slides)} slides)")
