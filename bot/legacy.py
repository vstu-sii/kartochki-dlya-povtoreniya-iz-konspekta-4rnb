"""Idempotent, non-destructive import of legacy Telegram-owned sets."""
import hashlib
from sqlalchemy import inspect, text
from bot.storage import Deck, Card

async def import_legacy(store):
    async with store.engine.connect() as connection:
        tables=await connection.run_sync(lambda c: inspect(c).get_table_names())
        if not {'study_sessions','card_sets','cards'} <= set(tables): return 0
        rows=(await connection.execute(text('SELECT DISTINCT user_id, card_set_id FROM study_sessions'))).all()
    imported=0
    for owner,set_id in rows:
        if not owner.startswith('telegram:') or not owner.split(':',1)[1].isdigit(): continue
        uid=int(owner.split(':',1)[1])
        await store.user(uid)
        did=hashlib.sha256(f'{uid}:{set_id}'.encode()).hexdigest()[:32]
        async with store.sessions.begin() as session:
            if await session.get(Deck,did): continue
            title=(await session.execute(text('SELECT title FROM card_sets WHERE id=:id'),{'id':set_id})).scalar()
            cards=(await session.execute(text('SELECT id, question, reference_answer, source_page, source_quote FROM cards WHERE card_set_id=:id ORDER BY position'),{'id':set_id})).mappings().all()
            if not title or not cards: continue
            session.add(Deck(id=did,user_id=uid,title=title))
            for c in cards:
                cid=hashlib.sha256(f'{uid}:{c["id"]}'.encode()).hexdigest()[:32]
                session.add(Card(id=cid,deck_id=did,user_id=uid,content={'question':c['question'],'answer':c['reference_answer'],'page':c['source_page'],'quote':c['source_quote']}))
            imported+=1
    return imported
