"""Honest stage/elapsed feedback; Telegram failures never cancel useful work."""
import asyncio
from contextlib import asynccontextmanager, suppress
import time

class Progress:
    def __init__(self, message, interval=8):
        self.message = message
        self.interval = interval
        self.stage = "Ожидаю свободное место"
        self.started = time.monotonic()
        self.status = None

    async def tick(self):
        seconds = int(time.monotonic() - self.started)
        text = f"⏳ {self.stage}…\nПрошло {seconds} с. Можно пользоваться меню."
        with suppress(Exception):
            async with asyncio.timeout(3):
                if self.status is None:
                    self.status = await self.message.answer(text)
                else:
                    await self.status.edit_text(text)
        bot = getattr(self.message, 'bot', None)
        chat = getattr(self.message, 'chat', None)
        if bot and chat:
            with suppress(Exception):
                async with asyncio.timeout(3):
                    await bot.send_chat_action(chat.id, 'typing')

    async def set(self, stage):
        self.stage = stage
        await self.tick()

    async def heartbeat(self):
        while True:
            await asyncio.sleep(self.interval)
            await self.tick()

@asynccontextmanager
async def progress(message, interval=8):
    state = Progress(message, interval)
    await state.tick()
    task = asyncio.create_task(state.heartbeat())
    try:
        yield state
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        if state.status:
            with suppress(Exception):
                async with asyncio.timeout(3):
                    await state.status.delete()
