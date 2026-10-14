"""HTTP adapter for the baseline model."""

from fastapi import FastAPI

from ml.models.baseline import BaselineModel


app = FastAPI(title="Flashcards AI Service", version="0.3.0")
model = BaselineModel()


@app.get("/health")
def health():
    return {"service": "ai-service", "status": "ok", "provider": model.provider}


@app.post("/v1/model/card-sets")
def generate(payload: dict):
    return model.generate(payload)


@app.post("/v1/model/answer-reviews")
def review(payload: dict):
    return model.review(payload)
