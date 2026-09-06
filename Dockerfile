# Заглушка на лабу 1. Реальный backend появится в лабе 2-3, тогда этот файл
# переедет на нормальную сборку приложения (например uvicorn/FastAPI или node).

FROM python:3.11-slim
WORKDIR /app
COPY docs/deploy/hello-world.html ./index.html
EXPOSE 8080
CMD ["python", "-m", "http.server", "8080"]
