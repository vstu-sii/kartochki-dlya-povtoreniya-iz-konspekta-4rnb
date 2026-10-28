from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import simpleSplit
from pathlib import Path

pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))
slides = [
 ('Карточки для устной защиты', 'Из конспекта PDF — в вопросы для повторения.\nDemo Day · лабораторная 6'),
 ('Проблема', 'Студенту трудно выделить важное в длинной методичке и проверить, может ли он объяснить материал своими словами.'),
 ('Решение', 'Telegram-бот принимает PDF, предлагает карточки с вопросами и источником, принимает ответ и помогает увидеть пробелы.'),
 ('Путь пользователя', 'Загрузить PDF → получить карточку → ответить своими словами → прочитать обратную связь → продолжить сессию.'),
 ('Как работает AI', 'Из PDF извлекается текст. Gemini предлагает вопросы и ответы по фрагментам. Приложение проверяет формат и цитаты, затем сохраняет карточки.'),
 ('Почему нам можно верить', 'Проверки структуры, цитат, регрессии и безопасности. Исходный live review agreement: 36 из 42, или 85,71%. После согласования трёх эталонов: 39 из 42 на тех же ответах.'),
 ('North Star', '1 из 1 внешних сессий достигла пяти карточек: 100% при цели 70%. Выборка n=1 слишком мала для надёжного вывода.'),
 ('Ограничения', 'Модель может ошибаться; содержание PDF не обязательно истинно. Последний публичный p95 проверки ответа — 31,990 с при n=5; цель 7 с пока не доказана.'),
 ('Демо и запасной план', 'Показываем публичный Telegram-бот и источник карточки. При отказе модели объясняем деградацию; при недоступности сервиса — заранее проверенное видео.'),
 ('Что дальше', 'Улучшить скорость и оценку ответов, расширить внешние наблюдения и перепроверить качество на финальной версии. Вопросы?'),
]
path = Path(__file__).with_name('presentation.pdf')
c = canvas.Canvas(str(path), pagesize=(960, 540))
for i,(title,body) in enumerate(slides,1):
 c.setFillColor(HexColor('#101c34')); c.rect(0,0,960,540,fill=1,stroke=0)
 c.setFillColor(HexColor('#52e2c2')); c.setFont('Arial',16); c.drawString(55,490,'DEMO DAY  /  КАРТОЧКИ ИЗ КОНСПЕКТА')
 c.setFillColor(HexColor('#ffffff')); c.setFont('Arial',32); c.drawString(55,415,title)
 c.setFillColor(HexColor('#d6e2f5')); c.setFont('Arial',21); y=340
 for para in body.split('\n'):
  for line in simpleSplit(para,'Arial',21,840): c.drawString(55,y,line); y-=34
  y-=10
 c.setFillColor(HexColor('#8ea6c8')); c.setFont('Arial',13); c.drawString(55,35,f'{i:02} / {len(slides):02}'); c.showPage()
c.save()
