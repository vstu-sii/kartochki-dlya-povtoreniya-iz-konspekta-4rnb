import pytest
from bot.storage import Store, next_interval


@pytest.fixture
async def store(tmp_path):
    db = Store(f"sqlite+aiosqlite:///{tmp_path / 'bot.db'}")
    await db.init()
    yield db
    await db.engine.dispose()


async def test_library_survives_restart_and_is_private(store):
    await store.user(1)
    await store.user(2)
    did = await store.save_deck(1, 'Тема', [{'question': 'Q', 'answer': 'A'}])
    cards = await store.cards(1, deck=did)
    assert len(cards) == 1
    assert not await store.cards(2, deck=did)
    assert await store.card(2, cards[0].id) is None
    await store.state(1, {'mode': 'study', 'queue': [cards[0].id], 'index': 0})
    second = Store(str(store.engine.url))
    try:
        assert (await second.user(1)).state['queue'] == [cards[0].id]
        assert len(await second.decks(1)) == 1
    finally:
        await second.engine.dispose()


async def test_repeat_is_idempotent(store):
    await store.user(1)
    did = await store.save_deck(1, 'Тема', [{'question': 'Q', 'answer': 'A'}])
    cid = (await store.cards(1, deck=did))[0].id
    assert await store.rate(1, cid, 'good', 'event-1', {'verdict': 'correct'})
    assert not await store.rate(1, cid, 'good', 'event-1', {})
    assert (await store.card(1, cid)).repetitions == 1
    assert not await store.cards(1, due=True)
    assert await store.stats(1) == (1, 0, 1)


async def test_reminders_opt_in_and_claim_once(store):
    await store.user(1)
    assert not await store.reminder_users()
    await store.settings(1, reminders=True)
    assert len(await store.reminder_users()) == 1
    assert await store.claim_reminder(1, '2026-11-01')
    assert not await store.claim_reminder(1, '2026-11-01')
    await store.finish_reminder(1, '2026-11-01')
    assert not await store.claim_reminder(1, '2026-11-01')
    assert await store.claim_reminder(1, '2026-11-02')


def test_intervals_adapt_to_difficulty():
    assert next_interval(0, 0, 'good') == (1, 1)
    assert next_interval(1, 1, 'good') == (3, 2)
    assert next_interval(30, 5, 'again') == (10 / 1440, 0)
    assert next_interval(180, 10, 'good')[0] == 180


async def test_generation_quota_is_persistent(store):
    await store.user(1)
    assert await store.allow_generation(1, limit=2)
    assert await store.allow_generation(1, limit=2)
    assert not await store.allow_generation(1, limit=2)


async def test_concurrent_first_contact_and_independent_writes(store):
    import asyncio
    users=await asyncio.gather(*(store.user(44) for _ in range(10)))
    assert all(u.id==44 for u in users)
    await asyncio.gather(*(store.save_deck(44,f'Topic {i}',[{'question':'Q','answer':'A'}]) for i in range(25)))
    assert (await store.stats(44))[0]==25
