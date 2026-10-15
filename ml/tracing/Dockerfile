FROM python:3.11-slim
WORKDIR /app
COPY dashboard.py .
ENV PORT=3000 TRACE_FILE=/data/traces.jsonl
EXPOSE 3000
CMD ["python", "dashboard.py"]
