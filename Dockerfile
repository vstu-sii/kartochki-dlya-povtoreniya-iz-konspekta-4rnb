FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY backend /app/backend
COPY ml /app/ml
COPY frontend/prototype /app/frontend
ENV PYTHONPATH=/app STATIC_DIR=/app/frontend AI_SERVICE_URL=inprocess DATABASE_URL=sqlite:////tmp/lab3.db PORT=10000
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
