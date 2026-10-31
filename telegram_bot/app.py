"""Aiogram adapter for the existing FastAPI/Compose topology."""
import asyncio
import os
from contextlib import asynccontextmanager, suppress
from pathlib import Path
import httpx
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Update, BotCommand
from fastapi import FastAPI
from bot import app as study
from bot.storage import Store
from bot.model import Model
from bot.legacy import import_legacy
from bot.observability import setup_logging, setup_tracing, measure_loop_lag
TOKEN=os.getenv('TELEGRAM_BOT_TOKEN','').strip()
_bot=None
_dispatcher=None
_client=None
_workers=[]
_listener=None
_tracing=None

async def configure_bot():
    global _bot,_dispatcher,_client,_listener,_tracing
    if _bot or not TOKEN: return
    Path('data').mkdir(exist_ok=True)
    study.store=Store(os.getenv('DATABASE_URL','sqlite+aiosqlite:///data/bot.db'))
    await study.store.init()
    await import_legacy(study.store)
    _listener=setup_logging()
    _tracing=setup_tracing()
    _client=httpx.AsyncClient()
    study.model=Model(_client)
    _bot=Bot(TOKEN,default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    _dispatcher=Dispatcher()
    _dispatcher.include_router(study.router)
    await _bot.set_my_commands([BotCommand(command=c,description=d) for c,d in [('start','Главное меню'),('library','Мои наборы'),('review','Повторить'),('new','Загрузить PDF'),('stats','Прогресс'),('settings','Напоминания'),('help','Помощь')]])
    _workers.extend([asyncio.create_task(study.reminders(_bot)),asyncio.create_task(measure_loop_lag())])

async def process_update(update):
    await _dispatcher.feed_update(_bot,Update.model_validate(update,context={'bot':_bot}))

async def telegram(method,payload=None):
    if method=='setWebhook': return await _bot.set_webhook(**(payload or {}))
    raise ValueError('Unsupported adapter method')

async def shutdown_bot():
    for task in _workers: task.cancel()
    for task in _workers:
        with suppress(asyncio.CancelledError): await task
    if _client: await _client.aclose()
    if _bot: await _bot.session.close()
    if study.store: await study.store.engine.dispose()
    if _tracing: await asyncio.to_thread(_tracing.shutdown)
    if _listener: _listener.stop()

@asynccontextmanager
async def lifespan(_):
    await configure_bot()
    polling=None
    if _bot:
        await _bot.delete_webhook(drop_pending_updates=False)
        polling=asyncio.create_task(_dispatcher.start_polling(_bot,close_bot_session=False,handle_signals=False))
    try: yield
    finally:
        if polling:
            polling.cancel()
            with suppress(asyncio.CancelledError): await polling
        await shutdown_bot()

app=FastAPI(lifespan=lifespan)

@app.get('/health')
async def health():
    from sqlalchemy import text
    from fastapi.responses import JSONResponse
    if study.store:
        try:
            async with study.store.engine.connect() as c: await c.execute(text('SELECT 1'))
        except Exception: return JSONResponse({'status':'database_unavailable'},status_code=503)
    return {'status':'ok','telegram':'aiogram' if _bot else 'not_configured'}


@app.get('/metrics')
async def metrics():
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from starlette.responses import Response
    return Response(generate_latest(),headers={'Content-Type':CONTENT_TYPE_LATEST})
