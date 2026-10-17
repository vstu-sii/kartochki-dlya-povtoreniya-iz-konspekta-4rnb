"""HTTP adapter for the baseline model."""

from fastapi import FastAPI

from ml.models.baseline import BaselineModel, PROMPT_VERSION, REVIEW_PROMPT_VERSION


app = FastAPI(title="Flashcards AI Service", version="0.4.0")
model = BaselineModel()


@app.get("/health")
def health():
    return {
        "service": "ai-service",
        "status": "ok",
        "provider": model.provider,
        "prompt_versions": {"generation": PROMPT_VERSION, "review": REVIEW_PROMPT_VERSION},
    }


@app.get("/v1/model/metadata")
def metadata():
    return {"prompt_versions": {"generation": PROMPT_VERSION, "review": REVIEW_PROMPT_VERSION}}


@app.post("/v1/model/card-sets")
def generate(payload: dict):
    return model.generate(payload)


@app.post("/v1/model/answer-reviews")
def review(payload: dict):
    return model.review(payload)
