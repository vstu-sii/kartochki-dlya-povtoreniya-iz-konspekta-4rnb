"""Telegram Bot API adapter with long polling.

The service remains healthy without a token so the repository is runnable by a
reviewer. Set TELEGRAM_BOT_TOKEN to enable the real Telegram interface.
"""

import asyncio
import html
import logging
import os
import re
import time
from collections import deque
from contextlib import asynccontextmanager, suppress
from io import BytesIO

import httpx
from fastapi import FastAPI


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
BACKEND_URL = (os.getenv("BACKEND_URL") or os.getenv("RENDER_EXTERNAL_URL") or "http://backend:8000").rstrip("/")
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}" if TOKEN else ""
TELEGRAM_FILE_API = f"https://api.telegram.org/file/bot{TOKEN}" if TOKEN else ""
sessions: dict[int, dict] = {}
recent_updates: deque[int] = deque(maxlen=1000)
recent_update_ids: set[int] = set()
action_times: dict[tuple[int, str], float] = {}
logger = logging.getLogger("telegram_bot")


async def telegram(method: str, payload: dict | None = None) -> dict:
    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=70.0) as client:
        for attempt in range(3):
            try:
                response = await client.post(f"{TELEGRAM_API}/{method}", json=payload or {})
                if response.status_code == 429:
                    retry_after = response.json().get("parameters", {}).get("retry_after", 1)
                    await asyncio.sleep(min(float(retry_after), 5.0))
                    continue
                response.raise_for_status()
                data = response.json()
                if not data.get("ok"):
                    raise RuntimeError(data.get("description", "Telegram API error"))
                return data["result"]
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt == 2 or isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500:
                    raise
                await asyncio.sleep(0.5 * (2**attempt))
    raise last_error or RuntimeError("Telegram API unavailable")


async def send(chat_id: int, text: str, reply_markup: dict | None = None, parse_mode: str | None = None) -> None:
    payload = {"chat_id": chat_id, "text": text[:4096], "disable_web_page_preview": True}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if parse_mode:
        payload["parse_mode"] = parse_mode
    await telegram("sendMessage", payload)


def review_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "👍 Полезно", "callback_data": "rate:useful"},
                {"text": "👎 Не полезно", "callback_data": "rate:not_useful"},
            ],
            [{"text": "➡️ Следующая карточка", "callback_data": "next"}],
        ]
    }


def card_keyboard() -> dict:
    return {"inline_keyboard": [[{"text": "⏭ Пропустить", "callback_data": "skip"}]]}


async def show_card(chat_id: int) -> None:
    state = sessions[chat_id]
    card = state["cards"][state["index"]]
    state["awaiting_answer"] = True
    question = html.escape(_compact(card["question"], 220))
    quote = html.escape(_compact(card["source_quote"], 260))
    await send(
        chat_id,
        f"📚 <b>Карточка {state['index'] + 1} из {len(state['cards'])}</b>\n\n"
        f"❓ <b>Вопрос</b>\n{question}\n\n"
        f"📖 <b>Источник · страница {card['source_page']}</b>\n<i>«{quote}»</i>\n\n"
        "✍️ Напишите ответ одним сообщением.",
        card_keyboard(),
        "HTML",
    )


def _compact(value: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", value).strip(" \n\r\t")
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip(" ,;:-") + "…"


async def create_from_pdf(chat_id: int, document: dict) -> None:
    await send(chat_id, "📄 PDF получен. Читаю текст, при необходимости применяю OCR и готовлю вопросы. Обычно это занимает до минуты…")
    file_info = await telegram("getFile", {"file_id": document["file_id"]})
    async with httpx.AsyncClient(timeout=90.0) as client:
        source = await client.get(f"{TELEGRAM_FILE_API}/{file_info['file_path']}")
        source.raise_for_status()
        response = await client.post(
            f"{BACKEND_URL}/v1/ai/card-sets/from-pdf",
            headers={"X-User-ID": f"telegram:{chat_id}"},
            files={"file": (document.get("file_name", "material.pdf"), BytesIO(source.content), "application/pdf")},
            data={"requested_card_count": "5", "language": "ru"},
        )
        response.raise_for_status()
        result = response.json()
        session_response = await client.post(
            f"{BACKEND_URL}/v1/ai/sessions",
            json={"card_set_id": result["card_set_id"], "user_id": f"telegram:{chat_id}"},
        )
        session_response.raise_for_status()
        persisted = session_response.json()
    sessions[chat_id] = {
        "session_id": persisted["session_id"],
        "cards": persisted["cards"],
        "index": persisted["current_position"],
        "ratings": persisted.get("ratings", {}),
        "awaiting_answer": False,
    }
    mode = "резервным алгоритмом" if result.get("fallback_used") else "языковой моделью"
    await send(chat_id, f"✅ Готово: создано {len(result['cards'])} карточек {mode}. Начинаем повторение.")
    await show_card(chat_id)


async def review_answer(chat_id: int, text: str) -> None:
    state = sessions[chat_id]
    card = state["cards"][state["index"]]
    async with httpx.AsyncClient(timeout=70.0, headers={"X-User-ID": f"telegram:{chat_id}"}) as client:
        response = await client.post(
            f"{BACKEND_URL}/v1/ai/answer-reviews",
            json={"session_id": state["session_id"], "card": card, "student_answer": text},
        )
        response.raise_for_status()
        result = response.json()
    state["awaiting_answer"] = False
    verdicts = {
        "correct": "✅ <b>Ответ верный</b>",
        "partially_correct": "🟡 <b>Ответ частично верный</b>",
        "incorrect": "🔴 <b>Ответ нужно доработать</b>",
    }
    missing = ", ".join(result.get("missing_points", []))
    message = f"{verdicts.get(result['verdict'], '📝 <b>Результат проверки</b>')}\n\n{html.escape(result['feedback'])}"
    if missing:
        message += f"\n\n<b>Стоит упомянуть:</b> {html.escape(missing)}"
    await send(chat_id, message, review_keyboard(), "HTML")


async def advance(chat_id: int, skipped: bool = False) -> None:
    state = sessions[chat_id]
    next_position = state["index"] + 1
    async with httpx.AsyncClient(timeout=20.0, headers={"X-User-ID": f"telegram:{chat_id}"}) as client:
        response = await client.patch(
            f"{BACKEND_URL}/v1/ai/sessions/{state['session_id']}/progress",
            json={"current_position": next_position},
        )
        response.raise_for_status()
    if next_position >= len(state["cards"]):
        state["index"] = len(state["cards"])
        state["awaiting_answer"] = False
        await send(
            chat_id,
            "🎉 <b>Повторение завершено!</b>\n\nВы прошли все карточки. "
            "Чтобы разобрать другой материал, используйте /new и отправьте новый PDF.",
            parse_mode="HTML",
        )
        return
    state["index"] = next_position
    if skipped:
        await send(chat_id, "Карточка пропущена. Перейдём к следующей.")
    await show_card(chat_id)


def _api_error_message(exc: httpx.HTTPStatusError) -> str:
    try:
        detail = exc.response.json().get("detail", {})
        code = detail.get("code") if isinstance(detail, dict) else None
    except Exception:
        code = None
    messages = {
        "PDF_TOO_LARGE": "PDF больше допустимых 10 МБ. Сожмите файл или разделите его.",
        "PDF_TOO_MANY_PAGES": "В PDF больше 40 страниц. Пришлите нужный раздел отдельным файлом.",
        "PDF_PASSWORD_PROTECTED": "PDF защищён паролем. Сохраните копию без пароля и отправьте её.",
        "PDF_PARSE_FAILED": "Файл повреждён или имеет неподдерживаемую структуру PDF.",
        "PDF_HAS_NO_READABLE_TEXT": "Не удалось распознать текст. Проверьте качество скана и попробуйте снова.",
        "OCR_FAILED": "Не удалось распознать скан. Попробуйте более чёткую версию PDF.",
        "OCR_UNAVAILABLE": "Распознавание сканов временно недоступно. Попробуйте PDF с текстовым слоем.",
        "AI_PROVIDER_UNAVAILABLE": "Сервис проверки временно недоступен. Попробуйте ещё раз через минуту.",
    }
    return "⚠️ " + messages.get(code, "Не удалось обработать файл. Проверьте PDF и попробуйте ещё раз.")


async def configure_bot() -> None:
    if not TOKEN:
        return
    await telegram(
        "setMyCommands",
        {
            "commands": [
                {"command": "start", "description": "Начать или продолжить обучение"},
                {"command": "new", "description": "Создать карточки из нового PDF"},
                {"command": "status", "description": "Показать прогресс"},
                {"command": "help", "description": "Как пользоваться ботом"},
                {"command": "privacy", "description": "Как обрабатываются данные"},
                {"command": "cancel", "description": "Отменить текущий ввод"},
            ]
        },
    )


async def process_update(update: dict) -> None:
    update_id = update.get("update_id")
    if update_id is not None:
        if update_id in recent_update_ids:
            return
        if len(recent_updates) == recent_updates.maxlen:
            recent_update_ids.discard(recent_updates[0])
        recent_updates.append(update_id)
        recent_update_ids.add(update_id)
    if callback := update.get("callback_query"):
        chat_id = callback["message"]["chat"]["id"]
        await telegram("answerCallbackQuery", {"callback_query_id": callback["id"]})
        action = callback.get("data", "")
        if action in {"next", "skip"} and chat_id in sessions:
            await advance(chat_id, skipped=action == "skip")
        elif action.startswith("rate:") and chat_id in sessions:
            state = sessions[chat_id]
            card = state["cards"][state["index"]]
            value = action.split(":", 1)[1]
            async with httpx.AsyncClient(timeout=20.0, headers={"X-User-ID": f"telegram:{chat_id}"}) as client:
                response = await client.put(
                    f"{BACKEND_URL}/v1/ai/sessions/{state['session_id']}/ratings/{card['card_id']}",
                    json={"value": value},
                )
                response.raise_for_status()
            state.setdefault("ratings", {})[card["card_id"]] = value
            await send(chat_id, "👍 Спасибо! Карточка отмечена как полезная." if value == "useful" else "👎 Спасибо! Учтём, что карточку нужно улучшить.", review_keyboard())
        return

    message = update.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    if not chat_id:
        return
    text = (message.get("text") or "").strip()
    command = text.split(maxsplit=1)[0].split("@", 1)[0].lower() if text.startswith("/") else ""
    if command == "/new":
        sessions.pop(chat_id, None)
        await send(chat_id, "📎 Пришлите новый PDF (до 10 МБ и 40 страниц). Можно отправить текстовый файл или качественный скан.")
    elif command == "/cancel":
        if chat_id in sessions:
            sessions[chat_id]["awaiting_answer"] = False
        await send(chat_id, "Текущий ввод отменён. Используйте /start для продолжения или /new для нового PDF.")
    elif command == "/status":
        state = sessions.get(chat_id)
        if state:
            if state["index"] >= len(state["cards"]):
                await send(chat_id, f"📊 Набор завершён: пройдено {len(state['cards'])} из {len(state['cards'])} карточек.")
            else:
                await send(chat_id, f"📊 Пройдено карточек: {state['index']} из {len(state['cards'])}. Текущая — {state['index'] + 1}.")
        else:
            await send(chat_id, "Активного набора нет. Используйте /start для восстановления или /new для нового PDF.")
    elif command == "/privacy":
        await send(
            chat_id,
            "🔐 PDF используется для создания карточек и не публикуется в Telegram. "
            "В технических трассах по умолчанию сохраняются только метаданные и хеш, без текста документа. "
            "Не отправляйте документы с паролями, паспортными, медицинскими или другими особо чувствительными данными.",
        )
    elif command == "/help":
        await send(
            chat_id,
            "<b>Как пользоваться</b>\n\n1. Отправьте PDF до 10 МБ и 40 страниц.\n"
            "2. Ответьте на каждый вопрос своими словами.\n3. Получите смысловую проверку и подсказку.\n"
            "4. Нажмите «Следующая карточка».\n\nКоманды: /new — новый файл, /status — прогресс, /privacy — данные.",
            parse_mode="HTML",
        )
    elif command == "/start":
        async with httpx.AsyncClient(timeout=20.0, headers={"X-User-ID": f"telegram:{chat_id}"}) as client:
            response = await client.get(f"{BACKEND_URL}/v1/ai/sessions/resume", params={"user_id": f"telegram:{chat_id}"})
        if response.status_code == 200:
            persisted = response.json()
            sessions[chat_id] = {
                "session_id": persisted["session_id"],
                "cards": persisted["cards"],
                "index": min(persisted["current_position"], len(persisted["cards"]) - 1),
                "ratings": persisted.get("ratings", {}),
                "awaiting_answer": False,
            }
            await send(chat_id, "👋 С возвращением! Продолжаем с карточки, на которой вы остановились.")
            await show_card(chat_id)
        else:
            await send(chat_id, "👋 <b>Здравствуйте!</b>\n\nПришлите PDF до 10 МБ и 40 страниц. Я прочитаю текст или распознаю скан, создам 5 содержательных карточек с источниками и проверю ответы по смыслу — формулировать дословно не нужно.", parse_mode="HTML")
    elif document := message.get("document"):
        now = time.monotonic()
        if now - action_times.get((chat_id, "pdf"), 0) < 15:
            await send(chat_id, "⏳ Предыдущий файл ещё обрабатывается. Подождите немного перед новой загрузкой.")
        elif document.get("mime_type") != "application/pdf" and not document.get("file_name", "").lower().endswith(".pdf"):
            await send(chat_id, "⚠️ Поддерживается только файл в формате PDF.")
        elif document.get("file_size", 0) > 10 * 1024 * 1024:
            await send(chat_id, "⚠️ Этот PDF больше 10 МБ. Пожалуйста, выберите файл поменьше.")
        else:
            action_times[(chat_id, "pdf")] = now
            try:
                await create_from_pdf(chat_id, document)
            except httpx.HTTPStatusError as exc:
                logger.warning("PDF processing rejected: status=%s", exc.response.status_code)
                await send(chat_id, _api_error_message(exc))
            except Exception:
                logger.exception("Unexpected PDF processing error")
                await send(chat_id, "⚠️ Не удалось обработать PDF из-за временной ошибки. Попробуйте ещё раз через минуту.")
    elif chat_id in sessions and sessions[chat_id].get("awaiting_answer") and text:
        now = time.monotonic()
        if now - action_times.get((chat_id, "answer"), 0) < 1.5:
            await send(chat_id, "⏳ Ответ уже проверяется. Подождите секунду.")
            return
        action_times[(chat_id, "answer")] = now
        try:
            await review_answer(chat_id, text)
        except Exception:
            logger.exception("Answer review failed")
            await send(chat_id, "⚠️ Сейчас не удалось проверить ответ. Пожалуйста, попробуйте ещё раз.")
    else:
        await send(chat_id, "Сначала отправьте PDF-методичку или используйте команду /help.")


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
    if TOKEN:
        await configure_bot()
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
