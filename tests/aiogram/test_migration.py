from sqlalchemy import text
from bot.storage import Store
from bot.legacy import import_legacy

async def test_import_preserves_old_data_and_owner(tmp_path):
    db=Store(f'sqlite+aiosqlite:///{tmp_path / "legacy.db"}')
    await db.init()
    async with db.engine.begin() as c:
        for sql in ['CREATE TABLE study_sessions (user_id TEXT, card_set_id TEXT)', 'CREATE TABLE card_sets (id TEXT,title TEXT)', 'CREATE TABLE cards (id TEXT,card_set_id TEXT,question TEXT,reference_answer TEXT,source_page INTEGER,source_quote TEXT,position INTEGER)', "INSERT INTO study_sessions VALUES ('telegram:123','set_old')", "INSERT INTO card_sets VALUES ('set_old','Old deck')", "INSERT INTO cards VALUES ('card_old','set_old','Q','A',1,'quote',1)"]:
            await c.execute(text(sql))
    assert await import_legacy(db)==1
    assert await import_legacy(db)==0
    assert len(await db.decks(123))==1
    assert len(await db.decks(456))==0
    assert (await db.cards(123))[0].content['answer']=='A'
    async with db.engine.connect() as c:
        assert (await c.execute(text('SELECT COUNT(*) FROM cards'))).scalar()==1
    await db.engine.dispose()
