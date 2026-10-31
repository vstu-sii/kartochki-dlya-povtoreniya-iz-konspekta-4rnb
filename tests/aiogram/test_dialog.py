from unittest.mock import AsyncMock
from types import SimpleNamespace
import pytest
from bot import app
from bot.storage import Store


def message(uid, text=''):
    return SimpleNamespace(from_user=SimpleNamespace(id=uid), text=text, message_id=101, answer=AsyncMock())


async def test_study_dialog_restart_and_stale_button(tmp_path, monkeypatch):
    db = Store(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    await db.init()
    monkeypatch.setattr(app, 'store', db)
    monkeypatch.setattr(app, 'model', SimpleNamespace(review=AsyncMock(return_value={'verdict': 'correct', 'feedback': 'Смысл верный'})))
    try:
        await db.user(42)
        deck = await db.save_deck(42, 'Test', [{'question': 'Что такое RAM?', 'answer': 'Оперативная память', 'quote': 'RAM', 'page': 1}])
        msg = message(42)
        callback = SimpleNamespace(from_user=msg.from_user, message=msg, data=f'deck:{deck}', answer=AsyncMock())
        await app.open_deck(callback)
        assert 'Что такое RAM?' in msg.answer.call_args.args[0]
        cid = (await db.user(42)).state['queue'][0]
        msg.text = 'Быстрая память для текущих программ'
        await app.answer(msg)
        assert (await db.user(42)).state['phase'] == 'grade'
        callback.data = f'grade:good:{cid}'
        await app.grade(callback)
        assert (await db.user(42)).state == {}
        assert await db.stats(42) == (1, 0, 1)
        await app.grade(callback)
        assert await db.stats(42) == (1, 0, 1)
        other = message(99)
        await db.user(99)
        callback.from_user = other.from_user
        callback.message = other
        callback.data = f'deck:{deck}'
        await app.open_deck(callback)
        assert other.answer.call_args.args[0] == 'Набор недоступен.'
    finally:
        await db.engine.dispose()
