FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app/ml
ENV PYTHONPATH=/app PORT=8001
EXPOSE 8001
CMD ["sh", "-c", "uvicorn ml.app:app --host 0.0.0.0 --port ${PORT:-8001}"]
