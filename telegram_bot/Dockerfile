FROM python:3.11-slim
WORKDIR /app
COPY telegram_bot/requirements.txt ./requirements.txt
COPY backend/requirements.txt ./backend-requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt -r backend-requirements.txt
COPY telegram_bot /app/telegram_bot
COPY bot /app/bot
COPY backend /app/backend
ENV PYTHONPATH=/app PORT=8002
EXPOSE 8002
CMD ["sh", "-c", "uvicorn telegram_bot.app:app --host 0.0.0.0 --port ${PORT:-8002}"]
