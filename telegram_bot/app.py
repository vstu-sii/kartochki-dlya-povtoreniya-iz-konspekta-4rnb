"""Telegram Bot API adapter with long polling.

The service remains healthy without a token so the repository is runnable by a
reviewer. Set TELEGRAM_BOT_TOKEN to enable the real Telegram interface.
"""

import asyncio
import os
from contextlib import asynccontextmanager, suppress
from io import BytesIO

import httpx
from fastapi import FastAPI


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000").rstrip("/")
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}" if TOKEN else ""
TELEGRAM_FILE_API = f"https://api.telegram.org/file/bot{TOKEN}" if TOKEN else ""
sessions: dict[int, dict] = {}


async def telegram(method: str, payload: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=70.0) as client:
        response = await client.post(f"{TELEGRAM_API}/{method}", json=payload or {})
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("description", "Telegram API error"))
        return data["result"]


async def send(chat_id: int, text: str, reply_markup: dict | None = None) -> None:
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    await telegram("sendMessage", payload)


def keyboard() -> dict:
    return {"inline_keyboard": [[{"text": "Следующая карточка", "callback_data": "next"}]]}


async def show_card(chat_id: int) -> None:
    state = sessions[chat_id]
    card = state["cards"][state["index"]]
    state["awaiting_answer"] = True
    await send(
        chat_id,
        f"Карточка {state['index'] + 1}/{len(state['cards'])}\n\n{card['question']}\n\n"
        f"Источник: стр. {card['source_page']} — «{card['source_quote']}»\n\n"
        "Отправьте ответ текстовым сообщением.",
        keyboard(),
    )


async def create_from_pdf(chat_id: int, document: dict) -> None:
    await send(chat_id, "Получил PDF. Извлекаю текст, создаю карточки и сохраняю результат…")
    file_info = await telegram("getFile", {"file_id": document["file_id"]})
    async with httpx.AsyncClient(timeout=90.0) as client:
        source = await client.get(f"{TELEGRAM_FILE_API}/{file_info['file_path']}")
        source.raise_for_status()
        response = await client.post(
            f"{BACKEND_URL}/v1/ai/card-sets/from-pdf",
            files={"file": (document.get("file_name", "material.pdf"), BytesIO(source.content), "application/pdf")},
            data={"requested_card_count": "5", "language": "ru"},
        )
        response.raise_for_status()
        result = response.json()
    sessions[chat_id] = {"cards": result["cards"], "index": 0, "awaiting_answer": False}
    await send(chat_id, f"Готово: {len(result['cards'])} карточек. Результат сохранён в БД.")
    await show_card(chat_id)


async def review_answer(chat_id: int, text: str) -> None:
    state = sessions[chat_id]
    card = state["cards"][state["index"]]
    async with httpx.AsyncClient(timeout=70.0) as client:
        response = await client.post(
            f"{BACKEND_URL}/v1/ai/answer-reviews",
            json={"session_id": f"tg_{chat_id}", "card": card, "student_answer": text},
        )
        response.raise_for_status()
        result = response.json()
    state["awaiting_answer"] = False
    missing = ", ".join(result.get("missing_points", [])) or "нет"
    await send(chat_id, f"{result['verdict']}: {result['feedback']}\nПропущено: {missing}", keyboard())


async def process_update(update: dict) -> None:
    if callback := update.get("callback_query"):
        chat_id = callback["message"]["chat"]["id"]
        await telegram("answerCallbackQuery", {"callback_query_id": callback["id"]})
        if callback.get("data") == "next" and chat_id in sessions:
            state = sessions[chat_id]
            state["index"] = (state["index"] + 1) % len(state["cards"])
            await show_card(chat_id)
        return

    message = update.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    if not chat_id:
        return
    text = (message.get("text") or "").strip()
    if text in {"/start", "/help"}:
        await send(chat_id, "Пришлите одну PDF-методичку. Я создам 5 карточек, покажу источники и проверю ответы.")
    elif document := message.get("document"):
        if document.get("mime_type") != "application/pdf":
            await send(chat_id, "Нужен файл PDF.")
        elif document.get("file_size", 0) > 10 * 1024 * 1024:
            await send(chat_id, "PDF больше 10 МБ. Для MVP выберите файл поменьше.")
        else:
            try:
                await create_from_pdf(chat_id, document)
            except Exception as exc:  # message is intentionally user-safe
                await send(chat_id, f"Не удалось обработать PDF: {type(exc).__name__}. Попробуйте ещё раз.")
    elif chat_id in sessions and sessions[chat_id].get("awaiting_answer") and text:
        try:
            await review_answer(chat_id, text)
        except Exception as exc:
            await send(chat_id, f"Не удалось проверить ответ: {type(exc).__name__}. Попробуйте ещё раз.")
    else:
        await send(chat_id, "Сначала отправьте PDF или используйте /help.")


async def poll() -> None:
    offset = 0
    while True:
        try:
            updates = await telegram("getUpdates", {"offset": offset, "timeout": 30, "allowed_updates": ["message", "callback_query"]})
            for update in updates:
                offset = update["update_id"] + 1
                await process_update(update)
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(3)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Production uses a Telegram webhook registered by backend.main. Local
    # Compose has no public URL, so the adapter uses long polling instead.
    task = asyncio.create_task(poll()) if TOKEN and not os.getenv("RENDER_EXTERNAL_URL") else None
    yield
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="Telegram Adapter", lifespan=lifespan)


@app.get("/health")
def health():
    return {"service": "telegram-bot", "status": "ok", "telegram": "enabled" if TOKEN else "token-not-configured"}
