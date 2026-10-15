"""FastAPI application entrypoint."""

import hashlib
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database import init_db
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
    init_db()
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
                "drop_pending_updates": True,
            },
        )
    yield


app = FastAPI(title="Карточки для повторения", version="0.3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(ai_router)


@app.get("/health")
def health():
    return {
        "service": "application-api",
        "status": "ok",
        "version": "lab3",
        "telegram": "webhook" if TELEGRAM_BOT_TOKEN and os.getenv("RENDER_EXTERNAL_URL") else "local-polling-or-disabled",
    }


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
