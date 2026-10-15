FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY backend /app/backend
COPY ml /app/ml
COPY telegram_bot /app/telegram_bot
COPY frontend/prototype /app/frontend
ENV PYTHONPATH=/app STATIC_DIR=/app/frontend AI_SERVICE_URL=inprocess BACKEND_URL=http://127.0.0.1:10000 DATABASE_URL=sqlite:////tmp/lab3.db PORT=10000 TRACE_CONTENT=false OCR_LANGUAGES=rus+eng
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
