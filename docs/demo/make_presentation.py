from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import simpleSplit
from pathlib import Path

pdfmetrics.registerFont(TTFont("Arial", "C:/Windows/Fonts/arial.ttf"))
pdfmetrics.registerFont(TTFont("ArialBold", "C:/Windows/Fonts/arialbd.ttf"))

# Цифры совпадают с lab6-ai-demo, lab6-delivery-demo и lab6-quality-demo на 30.10.2026.
# В Telegram источник и цитата не показываются: привязка проверяется в данных.
slides = [
    {
        "kicker": "DEMO DAY  ·  31.10.2026",
        "title": "Из длинного PDF — к устной защите",
        "lines": [
            "Карточки для повторения из конспекта",
            "Живое демо с прода, не с localhost",
        ],
    },
    {
        "kicker": "БОЛЬ",
        "title": "Методичку трудно превратить в проверку себя",
        "lines": [
            "Долго вручную делать вопросы по PDF",
            "Нельзя проверить ответ своими словами",
            "Неясно, на чём держится «правильный» ответ",
            "Прогресс между заходами теряется",
        ],
    },
    {
        "kicker": "РЕШЕНИЕ",
        "title": "Telegram: PDF → вопрос → разбор",
        "lines": [
            "Один конспект, пять карточек",
            "На экране вопрос. Страницу и цитату бот не показывает",
            "Привязка к тексту PDF проверяется в данных, не в чате",
            "Ответ своими словами и сохранённая сессия",
        ],
    },
    {
        "kicker": "ЧТО ПОКАЗЫВАЕМ",
        "title": "Публичный прод, тег v0.5.10-demo-candidate",
        "lines": [
            "kartochki-dlya-povtoreniya-iz-konspekta.onrender.com",
            "SHA a60eee706ad17238c11e0c79f53f026fd68bdf81",
            "UC-01: PDF → вопрос. UC-02: ответ → вердикт",
            "Фриз с 29.10.2026, 23:24 (Europe/Volgograd)",
        ],
    },
    {
        "kicker": "КАК РАБОТАЕТ AI",
        "title": "Модель предлагает, приложение проверяет",
        "lines": [
            "PDF → фрагменты → Gemini, строгая JSON Schema",
            "Контроль: 5 карточек и цитата есть в источнике",
            "Студент в Telegram видит вопрос и разбор, не цитату",
            "Отказ провайдера → «резервным алгоритмом», сессия цела",
        ],
    },
    {
        "kicker": "ЦИФРЫ",
        "title": "Одни и те же числа, что у AI и Quality",
        "lines": [
            "Schema / grounding: 100% / 100%",
            "Deterministic review: 90,48% → 90,48% → 92,86%",
            "Ablation: 92,86%; без правил 88,10%; lexical 71,43%",
            "Живой Gemini: 36/42 = 85,71%; те же ответы 39/42 = 92,86%",
        ],
    },
    {
        "kicker": "ПОЧЕМУ МОЖНО ВЕРИТЬ",
        "title": "Структура, цитата и тесты — с границей вывода",
        "lines": [
            "Цитата сверяется с PDF. Gates v0.5.10 — детерминированный режим",
            "Gemini: 36/42 = 85,71%; 39/42 = 92,86% — те же ответы, не новый прогон",
            "Review 90,48% / 90,48% / 92,86% — локальный алгоритм, не Gemini",
            "Публично 16/16 = 14 block + 2 allow. Локально 17/17 = 14 + 2 + 1 deny",
            "15/15 на теге: 1,777 / 2,909 с. Ранее 8,852 / 20,393 с — другой SHA",
        ],
    },
    {
        "kicker": "NORTH STAR",
        "title": "Доля сессий, дошедших до 5 карточек",
        "lines": [
            "Цель: ≥70% внешних сессий с current_position ≥ 5",
            "Факт: 1/1 = 100% (Постернак Денис, 15.10.2026)",
            "Замер по study_sessions",
            "n=1: цель на выборке есть, устойчивость — нет",
        ],
    },
    {
        "kicker": "КОМАНДА",
        "title": "Четыре роли на сцене",
        "lines": [
            "Product — Доброквашина Анастасия: история и тайминг",
            "Delivery — Ермакова Алиса: прод, бот, Plan B",
            "AI — Цвилева Вероника: пайплайн и вердикт",
            "Quality — Ткаченко София: evals и атаки",
        ],
    },
    {
        "kicker": "ОГРАНИЧЕНИЯ",
        "title": "Что блок доверия не обещает",
        "lines": [
            "Формат и цитата проверяются; истинность PDF — нет",
            "В Telegram источник не показывается: привязка только в данных",
            "Полезность: 2/3 = 66,67% при цели ≥80%, выборка мала",
            "X-User-ID — не логин, риск подмены пользователя высокий",
            "17/17 — обработчики с подменой модели; бинарный PDF не покрыт",
            "Скорость не гарантия: p95 31,990 с; цель review ≤7 с не доказана",
        ],
    },
    {
        "kicker": "PLAN B",
        "title": "Порог команды — 30 секунд",
        "lines": [
            "Дальше 30 с — записанное видео, прямо говорим «бэкап»",
            "Отказ Gemini — карточки «резервным алгоритмом»",
            "Нет сети — мобильный интернет, затем локальный файл",
            "Полный прогон команды: 7 минут",
        ],
    },
    {
        "kicker": "ЧТО ДАЛЬШЕ",
        "title": "Измерено. Выборка ещё мала",
        "lines": [
            "P0: ≥10 внешних сессий и ≥7 из 10 до пяти карточек",
            "Демо 31.10.2026, время не назначено",
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
    c.setFillColor(accent)
    c.drawString(48, 492, slide["kicker"])
    c.setFillColor(white)
    c.setFont("ArialBold", 28)
    y = 430
    for line in simpleSplit(slide["title"], "ArialBold", 28, 860):
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
    c.showPage()

c.save()
print(f"wrote {path} ({len(slides)} slides)")
