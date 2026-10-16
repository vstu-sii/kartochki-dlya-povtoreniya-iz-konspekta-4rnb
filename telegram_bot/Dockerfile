FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app/telegram_bot
ENV PYTHONPATH=/app PORT=8002
EXPOSE 8002
CMD ["sh", "-c", "uvicorn telegram_bot.app:app --host 0.0.0.0 --port ${PORT:-8002}"]
