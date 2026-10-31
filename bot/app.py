"""Aiogram private-chat UI; async IO, durable study state and opt-in reminders."""
import asyncio
import hashlib
import hmac
import html
import logging
import os
from collections import defaultdict
from contextlib import suppress
from datetime import datetime
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo
from uuid import uuid4

import httpx
from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command, CommandStart
from aiogram.types import BotCommand, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, Message, ReplyKeyboardMarkup, Update

from bot.model import Model, ModelUnavailable, extract_pdf
from bot.storage import Store
from bot.observability import measured, operation, setup_logging, setup_tracing, measure_loop_lag, REMINDERS
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

log = logging.getLogger(__name__)
router = Router()
router.message.filter(F.chat.type == "private")
router.callback_query.filter(F.message.chat.type == "private")
store = None
model = None
locks = defaultdict(asyncio.Lock)
jobs = asyncio.Semaphore(4)
MENU = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📚 Мои наборы"), KeyboardButton(text="🔁 Повторить")],
    [KeyboardButton(text="➕ Загрузить PDF"), KeyboardButton(text="📊 Прогресс")],
    [KeyboardButton(text="🔔 Напоминания"), KeyboardButton(text="❓ Помощь")]], resize_keyboard=True)


def keyboard(rows):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=d) for t, d in row] for row in rows])


def esc(text):
    return html.escape(str(text))


async def metrics_response(request):
    token=request.app.get('metrics_token','')
    if not token:
        raise web.HTTPNotFound()
    if not hmac.compare_digest(request.headers.get('Authorization',''), f'Bearer {token}'):
        raise web.HTTPUnauthorized()
    return web.Response(body=generate_latest(),headers={'Content-Type':CONTENT_TYPE_LATEST})


async def user(uid):
    return await store.user(uid, os.getenv("DEFAULT_TIMEZONE", "Europe/Volgograd"))


@router.message(CommandStart())
@router.message(Command("menu", "cancel"))
async def start(message: Message):
    await user(message.from_user.id)
    await message.answer("📚 <b>Карточки для повторения</b>\n\nЗагрузите PDF, сохраните вопросы и возвращайтесь к ним в удобное время.\n\nОтветы можно писать своими словами. Для регулярных занятий включите напоминания в меню.", reply_markup=MENU)


@router.message(Command("help", "privacy"))
@router.message(F.text == "❓ Помощь")
async def help_message(message: Message):
    await message.answer("<b>Как заниматься</b>\n1. Отправьте текстовый PDF до 10 МБ и 40 страниц.\n2. Выберите 5 или 10 карточек.\n3. Ответьте своими словами или откройте эталон.\n4. Оцените сложность — от неё зависит следующее повторение.\n\nВсе наборы остаются в библиотеке. Меню «Повторить» показывает карточки, срок которых наступил.\n\n<b>Данные:</b> хранятся Telegram ID, карточки, прогресс и настройки. PDF обрабатывается в памяти; извлечённый текст и ответы передаются Google Gemini. Не отправляйте чувствительные документы. Полный текст промптов в логи не записывается. Оценка AI может ошибаться; окончательную сложность выбираете вы.", reply_markup=MENU)


@router.message(F.text == "➕ Загрузить PDF")
@router.message(Command("new"))
async def upload_hint(message: Message):
    await user(message.from_user.id)
    await message.answer("📎 Отправьте текстовый PDF до 10 МБ и 40 страниц. Сохранённые наборы останутся в библиотеке.")


@router.message(F.document)
async def receive_pdf(message: Message):
    uid = message.from_user.id
    await user(uid)
    if locks[uid].locked():
        await message.answer("⏳ Дождитесь завершения предыдущего запроса перед загрузкой нового файла.")
        return
    doc = message.document
    if not (doc.file_name or "").lower().endswith(".pdf"):
        await message.answer("Поддерживается PDF. Выберите документ с расширением .pdf.")
        return
    if (doc.file_size or 0) > 10 * 1024 * 1024:
        await message.answer("Файл больше 10 МБ. Разделите его на главы.")
        return
    await store.state(uid, {"mode": "upload", "file_id": doc.file_id, "name": doc.file_name})
    await message.answer("Сколько карточек подготовить?", reply_markup=keyboard([[('5 карточек', 'generate:5'), ('10 карточек', 'generate:10')]]))


@router.callback_query(F.data.startswith("generate:"))
@measured('telegram.generate')
async def generate(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    uid = callback.from_user.id
    if locks[uid].locked():
        await callback.message.answer("⏳ Ваш запрос ещё выполняется.")
        return
    async with locks[uid]:
        state = (await user(uid)).state
        if state.get("mode") != "upload":
            await callback.message.answer("Этот файл уже обработан. Отправьте новый PDF или откройте библиотеку.")
            return
        count = int(callback.data.split(":")[1])
        if count not in {5, 10}:
            return
        if not await store.allow_generation(uid):
            await callback.message.answer("На сегодня достигнут лимит: 10 попыток генерации. Завтра можно продолжить; сохранённые наборы доступны сейчас.")
            return
        await callback.message.answer("⏳ Читаю PDF и составляю вопросы. Можно продолжать пользоваться меню.")
        try:
            async with jobs:
                buffer = BytesIO()
                await bot.download(state["file_id"], destination=buffer, timeout=45)
                raw = buffer.getvalue()
                if len(raw) > 10 * 1024 * 1024:
                    raise ValueError("Файл больше 10 МБ.")
                with operation('pdf.extract'):
                    pages = await asyncio.to_thread(extract_pdf, raw)
                title, cards = await model.generate(pages, count)
                deck_id = await store.save_deck(uid, title, cards)
            await store.state(uid, {})
            await callback.message.answer(f"✅ <b>{esc(title)}</b>\nСохранено карточек: {len(cards)}. Набор доступен в библиотеке.", reply_markup=keyboard([[('Начать занятие', f'deck:{deck_id}')]]))
        except (ValueError, ModelUnavailable) as exc:
            await callback.message.answer(esc(str(exc)))
        except Exception:
            log.exception("PDF job failed")
            await callback.message.answer("Не удалось обработать PDF. Наборы в библиотеке сохранены. Попробуйте снова позже.")


async def library(message, uid, offset=0):
    await user(uid)
    decks = await store.decks(uid, offset)
    if not decks:
        await message.answer("Пока нет наборов. Отправьте PDF — первые карточки появятся здесь.", reply_markup=MENU)
        return
    rows = [[(d.title[:45], f"deck:{d.id}")] for d in decks[:8]]
    nav = []
    if offset:
        nav.append(("← Назад", f"library:{max(0, offset-8)}"))
    if len(decks) > 8:
        nav.append(("Далее →", f"library:{offset+8}"))
    if nav:
        rows.append(nav)
    await message.answer("📚 <b>Ваши наборы</b>\nВыберите тему для занятия.", reply_markup=keyboard(rows))


@router.message(F.text == "📚 Мои наборы")
@router.message(Command("library"))
async def library_message(message: Message):
    await library(message, message.from_user.id)


@router.callback_query(F.data.startswith("library:"))
async def library_page(callback: CallbackQuery):
    await callback.answer()
    await library(callback.message, callback.from_user.id, max(0, int(callback.data.split(":")[1])))


async def show_card(message, uid):
    state = (await user(uid)).state
    queue = state.get("queue", [])
    index = state.get("index", 0)
    if index >= len(queue):
        await store.state(uid, {})
        await message.answer("🎉 <b>Занятие завершено!</b>\nСложные карточки вернутся раньше, знакомые — позже. Расписание сохранено.", reply_markup=MENU)
        return
    card = await store.card(uid, queue[index])
    if not card:
        await store.state(uid, {})
        await message.answer("Карточка недоступна. Откройте библиотеку.")
        return
    await message.answer(f"<b>Карточка {index+1} из {len(queue)}</b>\n\n{esc(card.content['question'])}\n\n✍️ Напишите ответ своими словами.", reply_markup=keyboard([[('👁 Показать ответ', f'reveal:{card.id}')]]))


@router.callback_query(F.data.startswith("deck:"))
@measured('telegram.open_deck')
async def open_deck(callback: CallbackQuery):
    await callback.answer()
    uid = callback.from_user.id
    async with locks[uid]:
        cards = await store.cards(uid, deck=callback.data.split(":")[1])
        if not cards:
            await callback.message.answer("Набор недоступен.")
            return
        state = (await user(uid)).state
        ids = [c.id for c in cards]
        if state.get("mode") != "study" or state.get("queue") != ids:
            await store.state(uid, {"mode": "study", "queue": ids, "index": 0, "phase": "answer", "cycle": uuid4().hex})
        await show_card(callback.message, uid)


@router.message(F.text == "🔁 Повторить")
@router.message(Command("review"))
async def repeat(message: Message):
    uid = message.from_user.id
    await user(uid)
    async with locks[uid]:
        current = (await user(uid)).state
        if current.get("mode") == "study":
            await show_card(message, uid)
            return
        cards = await store.cards(uid, due=True)
        if not cards:
            await message.answer("✨ На сегодня всё повторено. Можно открыть любой набор в библиотеке.", reply_markup=MENU)
            return
        await store.state(uid, {"mode": "study", "queue": [c.id for c in cards], "index": 0, "phase": "answer", "cycle": uuid4().hex})
        await show_card(message, uid)


def grade_keyboard(cid):
    return keyboard([[('Снова · 10 мин', f'grade:again:{cid}')], [('Трудно', f'grade:hard:{cid}'), ('Знаю', f'grade:good:{cid}')]])


async def active_card(uid, cid=None, phase=None):
    state = (await user(uid)).state
    i = state.get("index", 0)
    queue = state.get("queue", [])
    if state.get("mode") != "study" or i >= len(queue) or (cid and queue[i] != cid) or (phase and state.get("phase") != phase):
        return None, None
    return state, await store.card(uid, queue[i])


@router.callback_query(F.data.startswith("reveal:"))
async def reveal(callback: CallbackQuery):
    await callback.answer()
    uid = callback.from_user.id
    async with locks[uid]:
        state, card = await active_card(uid, callback.data.split(":")[1])
        if not card:
            await callback.message.answer("Это кнопка от предыдущей карточки. Откройте «Повторить».")
            return
        state = {**state, "phase": "grade", "result": {"verdict": "self_review"}}
        await store.state(uid, state)
        await callback.message.answer(f"📖 <b>Эталонный ответ</b>\n\n{esc(card.content['answer'])}\n\nНасколько легко вы вспомнили материал?", reply_markup=grade_keyboard(card.id))


@router.callback_query(F.data.startswith("grade:"))
@measured('telegram.grade')
async def grade(callback: CallbackQuery):
    await callback.answer()
    uid = callback.from_user.id
    async with locks[uid]:
        _, value, cid = callback.data.split(":")
        state, card = await active_card(uid, cid, "grade")
        if not card or value not in {"again", "hard", "good"}:
            return
        event_id = f"{state.get('cycle', uid)}:{state['index']}"
        next_state = {**state, "index": state['index']+1, "phase": "answer", "result": {}}
        await store.rate(uid, cid, value, event_id, state.get("result", {}), next_state=next_state)
        await show_card(callback.message, uid)


@router.message(F.text == "📊 Прогресс")
@router.message(Command("stats"))
async def stats(message: Message):
    uid = message.from_user.id
    await user(uid)
    total, due, reviews = await store.stats(uid)
    await message.answer(f"📊 <b>Ваш прогресс</b>\n\nКарточек: {total}\nПора повторить: {due}\nПовторений завершено: {reviews}\n\nЭто статистика занятий, а не доказанный процент запоминания.", reply_markup=MENU)


async def settings_view(message, uid):
    u = await user(uid)
    await message.answer(f"🔔 <b>Напоминания</b>\n\n{'Включены' if u.reminders else 'Выключены'} · {u.reminder_hour:02d}:00\nЧасовой пояс: {esc(u.timezone)}\n\nНе больше одного напоминания в день и только когда есть карточки к повторению.", reply_markup=keyboard([
        [('Выключить' if u.reminders else 'Включить', f'notify:{0 if u.reminders else 1}')],
        [('09:00', 'hour:9'), ('14:00', 'hour:14'), ('19:00', 'hour:19')],
        [('Москва / Волгоград', 'tz:Europe/Volgograd')],
        [('Екатеринбург', 'tz:Asia/Yekaterinburg'), ('Новосибирск', 'tz:Asia/Novosibirsk')]]))


@router.message(F.text == "🔔 Напоминания")
@router.message(Command("settings"))
async def settings(message: Message):
    await settings_view(message, message.from_user.id)


@router.callback_query(F.data.startswith("notify:") | F.data.startswith("hour:") | F.data.startswith("tz:"))
async def change_settings(callback: CallbackQuery):
    await callback.answer()
    uid = callback.from_user.id
    await user(uid)
    key, value = callback.data.split(":", 1)
    if key == "notify" and value in {"0", "1"}:
        await store.settings(uid, reminders=value == "1")
    elif key == "hour" and value in {"9", "14", "19"}:
        await store.settings(uid, reminder_hour=int(value))
    elif key == "tz" and value in {"Europe/Volgograd", "Asia/Yekaterinburg", "Asia/Novosibirsk"}:
        await store.settings(uid, timezone=value)
    await settings_view(callback.message, uid)


@router.message(F.text)
@measured('telegram.answer')
async def answer(message: Message):
    uid = message.from_user.id
    await user(uid)
    if locks[uid].locked():
        await message.answer("⏳ Ваш ответ ещё проверяется. Подождите немного.")
        return
    async with locks[uid]:
        state, card = await active_card(uid, phase="answer")
        if not card:
            await message.answer("Выберите действие в меню или отправьте PDF.", reply_markup=MENU)
            return
        if len(message.text) > 2000:
            await message.answer("Ответ слишком длинный. Уложитесь в 2000 символов.")
            return
        await message.answer("⏳ Сравниваю смысл ответа с материалом…")
        try:
            result = await model.review(card.content, message.text)
            await store.state(uid, {**state, "phase": "grade", "result": result})
            titles = {"correct": "✅ Верно", "partial": "🟡 Частично верно", "incorrect": "📝 Есть что повторить"}
            await message.answer(f"<b>{titles[result['verdict']]}</b>\n\n{esc(result['feedback'])}\n\n<b>Эталон</b>\n{esc(card.content['answer'])}\n\nAI может ошибаться. Выберите сложность по своим ощущениям:", reply_markup=grade_keyboard(card.id))
        except ModelUnavailable as exc:
            await message.answer(esc(str(exc)), reply_markup=keyboard([[('Открыть эталон', f'reveal:{card.id}')]]))


async def reminders(bot):
    while True:
        try:
            for u in await store.reminder_users():
                local = datetime.now(ZoneInfo(u.timezone))
                if local.hour != u.reminder_hour or not (await store.cards(u.id, due=True)):
                    continue
                day = local.date().isoformat()
                if not await store.claim_reminder(u.id, day):
                    continue
                try:
                    await bot.send_message(u.id, "🔁 Пора ненадолго вернуться к карточкам. Откройте «Повторить» — начнём с тех, которые уже подошли по расписанию.", reply_markup=MENU)
                    await store.finish_reminder(u.id, day)
                    REMINDERS.labels('sent').inc()
                except TelegramForbiddenError:
                    REMINDERS.labels('blocked').inc()
                    await store.settings(u.id, reminders=False)
                except TelegramRetryAfter as exc:
                    REMINDERS.labels('rate_limited').inc()
                    await asyncio.sleep(min(exc.retry_after, 60))
                await asyncio.sleep(0.1)
        except Exception:
            log.exception("Reminder worker failed")
        await asyncio.sleep(60)


async def main():
    global store, model
    listener=setup_logging()
    tracing=setup_tracing()
    # Never log request URLs: provider keys belong in headers only.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN")
    Path("data").mkdir(exist_ok=True)
    store = Store(os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/bot.db"))
    await store.init()
    bot = Bot(token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    client = httpx.AsyncClient()
    model = Model(client)
    await bot.set_my_commands([BotCommand(command=c, description=d) for c, d in [('start','Главное меню'),('library','Мои наборы'),('review','Повторить'),('new','Загрузить PDF'),('stats','Прогресс'),('settings','Напоминания'),('help','Помощь')]])
    worker = asyncio.create_task(reminders(bot))
    lag_worker=asyncio.create_task(measure_loop_lag())
    app = web.Application(client_max_size=2 * 1024 * 1024)
    async def health(_):
        from sqlalchemy import text
        try:
            async with store.engine.connect() as c:
                await c.execute(text("SELECT 1"))
        except Exception:
            return web.json_response({"status": "database_unavailable"}, status=503)
        return web.json_response({"status": "ok", "version": "aiogram-v1", "commit_sha": os.getenv("RENDER_GIT_COMMIT", "local")})
    app.router.add_get('/health', health)
    metrics_token=os.getenv('METRICS_TOKEN','')
    if os.getenv('METRICS_TOKEN_FILE'):
        metrics_token=Path(os.environ['METRICS_TOKEN_FILE']).read_text().strip()
    app['metrics_token']=metrics_token
    app.router.add_get('/metrics',metrics_response)
    public = os.getenv('WEBHOOK_BASE_URL', '').rstrip('/')
    secret = os.getenv('WEBHOOK_SECRET') or hashlib.sha256(token.encode()).hexdigest()
    async def webhook(request):
        if not hmac.compare_digest(request.headers.get('X-Telegram-Bot-Api-Secret-Token', ''), secret):
            raise web.HTTPForbidden()
        update = Update.model_validate(await request.json(), context={"bot": bot})
        # Aiogram acknowledges quickly while handlers await async network/DB IO.
        result = await dp.feed_webhook_update(bot, update)
        return web.json_response(result if isinstance(result, dict) else {})
    app.router.add_post('/telegram/webhook', webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.getenv('PORT', '10000'))).start()
    try:
        if public:
            await bot.set_webhook(f'{public}/telegram/webhook', secret_token=secret, drop_pending_updates=False, allowed_updates=dp.resolve_used_update_types())
            await asyncio.Event().wait()
        else:
            await bot.delete_webhook(drop_pending_updates=False)
            await dp.start_polling(bot, close_bot_session=False)
    finally:
        worker.cancel()
        lag_worker.cancel()
        with suppress(asyncio.CancelledError):
            await worker
        with suppress(asyncio.CancelledError):
            await lag_worker
        await runner.cleanup()
        await client.aclose()
        await bot.session.close()
        await store.engine.dispose()
        await asyncio.to_thread(tracing.shutdown)
        listener.stop()


if __name__ == '__main__':
    asyncio.run(main())
