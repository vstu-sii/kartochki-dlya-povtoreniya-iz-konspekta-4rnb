"""FastAPI application entrypoint."""

import hashlib
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from backend.database import init_db
from backend.observability import metrics_middleware, metrics_response
from backend.routers.ai import router as ai_router
try:
    # The single-container Render image includes the adapter. In local Compose
    # it runs as its own service, so the backend image intentionally omits it.
    from telegram_bot.app import TOKEN as TELEGRAM_BOT_TOKEN
    from telegram_bot.app import configure_bot, process_update, telegram
except ModuleNotFoundError:  # local multi-container topology
    TELEGRAM_BOT_TOKEN = ""
    process_update = None
    telegram = None
    configure_bot = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    import asyncio
    await asyncio.to_thread(init_db)
    public_url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
    if TELEGRAM_BOT_TOKEN and public_url and telegram:
        if configure_bot:
            await configure_bot()
        secret = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode()).hexdigest()
        await telegram(
            "setWebhook",
            {
                "url": f"{public_url}/telegram/webhook",
                "secret_token": secret,
                "allowed_updates": ["message", "callback_query"],
                "drop_pending_updates": False,
            },
        )
    try:
        yield
    finally:
        if configure_bot:
            from telegram_bot.app import shutdown_bot
            await shutdown_bot()


APP_VERSION = os.getenv("APP_VERSION", "lab5")

app = FastAPI(title="Карточки для повторения", version="0.5.0", lifespan=lifespan)
app.middleware("http")(metrics_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(ai_router)


@app.exception_handler(SQLAlchemyError)
async def database_unavailable(_: Request, __: SQLAlchemyError):
    """Return a stable degradation contract instead of leaking HTTP 500."""
    return JSONResponse(status_code=503,
                        content={"detail": {"code": "DATABASE_UNAVAILABLE", "retryable": True}},
                        headers={"Retry-After": "5"})


@app.get("/health")
def health():
    from backend.database import engine
    from sqlalchemy import text
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {
        "service": "application-api",
        "status": "ok",
        "version": APP_VERSION,
        "commit_sha": os.getenv("RENDER_GIT_COMMIT", os.getenv("COMMIT_SHA", "unknown")),
        "telegram_adapter": "aiogram",
        "telegram": "webhook" if TELEGRAM_BOT_TOKEN and os.getenv("RENDER_EXTERNAL_URL") else "local-polling-or-disabled",
    }


@app.get("/metrics", include_in_schema=False)
def metrics():
    response=metrics_response()
    if TELEGRAM_BOT_TOKEN:
        from prometheus_client import generate_latest
        from starlette.responses import Response
        return Response(response.body + b"\n" + generate_latest(),media_type="text/plain; version=0.0.4")
    return response


@app.post("/telegram/webhook", include_in_schema=False)
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    telegram_secret: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token"),
):
    if not TELEGRAM_BOT_TOKEN or not process_update:
        raise HTTPException(status_code=404)
    expected = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode()).hexdigest()
    if telegram_secret != expected:
        raise HTTPException(status_code=403)
    # Telegram expects a quick acknowledgement. PDF/OCR/model processing runs
    # after the HTTP response, and duplicate update IDs are ignored by adapter.
    background_tasks.add_task(process_update, await request.json())
    return {"ok": True}


static_dir = Path(os.getenv("STATIC_DIR", "/app/frontend"))
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
