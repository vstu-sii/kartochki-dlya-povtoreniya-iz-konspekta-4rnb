"""Async persistence. All ownership checks happen in repository queries."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import BigInteger, Boolean, Float, Integer, JSON, String, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import event
import time
from bot.observability import DB_DURATION, DB_ERRORS


def now():
    return datetime.now(timezone.utc).timestamp()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "tg_users"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Volgograd")
    reminder_hour: Mapped[int] = mapped_column(Integer, default=19)
    reminders: Mapped[bool] = mapped_column(Boolean, default=False)
    last_reminder_day: Mapped[str] = mapped_column(String(10), default="")
    reminder_lease: Mapped[float] = mapped_column(Float, default=0)
    state: Mapped[dict] = mapped_column(JSON, default=dict)
    generation_day: Mapped[str] = mapped_column(String(10), default="")
    generation_count: Mapped[int] = mapped_column(Integer, default=0)


class Deck(Base):
    __tablename__ = "tg_decks"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid4().hex)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    title: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[float] = mapped_column(Float, default=now)


class Card(Base):
    __tablename__ = "tg_cards"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid4().hex)
    deck_id: Mapped[str] = mapped_column(String(32), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    content: Mapped[dict] = mapped_column(JSON)
    due: Mapped[float] = mapped_column(Float, default=now, index=True)
    interval_days: Mapped[float] = mapped_column(Float, default=0)
    repetitions: Mapped[int] = mapped_column(Integer, default=0)


class Review(Base):
    __tablename__ = "tg_reviews"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    card_id: Mapped[str] = mapped_column(String(32))
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[float] = mapped_column(Float, default=now)


def next_interval(previous: float, repetitions: int, grade: str):
    if grade == "again":
        return 10 / 1440, 0
    if grade == "hard":
        return max(1, previous * 1.2), repetitions
    if grade == "good":
        return (1 if repetitions == 0 else 3 if repetitions == 1 else min(180, previous * 2.2)), repetitions + 1
    raise ValueError("Unknown review grade")


class Store:
    def __init__(self, url, *, sqlite_serialized=True):
        if url.startswith("sqlite:///"):
            url = url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        if url.startswith("postgresql+psycopg://"):
            url = url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        options={}
        if url.startswith('sqlite') and sqlite_serialized:
            from sqlalchemy.pool import AsyncAdaptedQueuePool
            # SQLite has one writer. Queue transactions asynchronously instead
            # of opening many competing write connections. PostgreSQL keeps
            # its ordinary connection pool and row locks.
            options.update(poolclass=AsyncAdaptedQueuePool,pool_size=1,max_overflow=0,pool_timeout=30,connect_args={'timeout':30})
        self.engine = create_async_engine(url, pool_pre_ping=True, **options)
        if url.startswith('sqlite') and sqlite_serialized:
            @event.listens_for(self.engine.sync_engine,'connect')
            def configure_sqlite(connection,record):
                cursor=connection.cursor()
                cursor.execute('PRAGMA journal_mode=WAL')
                cursor.execute('PRAGMA busy_timeout=30000')
                cursor.close()
        @event.listens_for(self.engine.sync_engine,'before_cursor_execute')
        def before(conn,cursor,statement,parameters,context,executemany):
            context.telemetry_started=time.perf_counter()
        @event.listens_for(self.engine.sync_engine,'after_cursor_execute')
        def after(conn,cursor,statement,parameters,context,executemany):
            verb=statement.lstrip().split(' ',1)[0].upper()
            label=verb if verb in {'SELECT','INSERT','UPDATE','DELETE','PRAGMA','CREATE'} else 'OTHER'
            DB_DURATION.labels(label).observe(time.perf_counter()-context.telemetry_started)
        @event.listens_for(self.engine.sync_engine,'handle_error')
        def failure(context):
            DB_ERRORS.inc()
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def init(self):
        async with self.engine.begin() as c:
            await c.run_sync(Base.metadata.create_all)

    async def user(self, uid, tz="Europe/Volgograd"):
        async with self.sessions() as s:
            u = await s.get(User, uid)
            if u is None:
                if self.engine.dialect.name=='sqlite':
                    from sqlalchemy.dialects.sqlite import insert
                else:
                    from sqlalchemy.dialects.postgresql import insert
                await s.execute(insert(User).values(id=uid,timezone=tz).on_conflict_do_nothing(index_elements=['id']))
                await s.commit()
                u=await s.get(User,uid)
            return u

    async def state(self, uid, state):
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id == uid).values(state=state))

    async def allow_generation(self, uid, limit=10):
        day = datetime.now(timezone.utc).date().isoformat()
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id == uid, User.generation_day != day).values(generation_day=day, generation_count=0))
            r = await s.execute(update(User).where(User.id == uid, User.generation_count < limit).values(generation_count=User.generation_count + 1))
            return r.rowcount == 1

    async def settings(self, uid, **values):
        allowed = {k: v for k, v in values.items() if k in {"reminders", "timezone", "reminder_hour"}}
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id == uid).values(**allowed))

    async def save_deck(self, uid, title, cards):
        async with self.sessions.begin() as s:
            d = Deck(user_id=uid, title=title[:200])
            s.add(d)
            await s.flush()
            s.add_all([Card(deck_id=d.id, user_id=uid, content=c) for c in cards])
            return d.id

    async def decks(self, uid, offset=0):
        async with self.sessions() as s:
            return list((await s.scalars(select(Deck).where(Deck.user_id == uid).order_by(Deck.created_at.desc()).offset(offset).limit(9))).all())

    async def cards(self, uid, deck=None, due=False):
        q = select(Card).where(Card.user_id == uid)
        if deck:
            q = q.where(Card.deck_id == deck)
        if due:
            q = q.where(Card.due <= now())
        async with self.sessions() as s:
            return list((await s.scalars(q.order_by(Card.due, Card.id).limit(50))).all())

    async def card(self, uid, cid):
        async with self.sessions() as s:
            return await s.scalar(select(Card).where(Card.id == cid, Card.user_id == uid))

    async def rate(self, uid, cid, grade, event_id, result, next_state=None):
        async with self.sessions.begin() as s:
            if await s.get(Review, event_id):
                return False
            c = await s.scalar(select(Card).where(Card.id == cid, Card.user_id == uid).with_for_update())
            if c is None:
                raise ValueError("Card not owned")
            interval, repetitions = next_interval(c.interval_days, c.repetitions, grade)
            c.interval_days, c.repetitions = interval, repetitions
            c.due = now() + interval * 86400
            s.add(Review(id=event_id, user_id=uid, card_id=cid, result={**result, "grade": grade}))
            if next_state is not None:
                await s.execute(update(User).where(User.id == uid).values(state=next_state))
            return True

    async def stats(self, uid):
        from sqlalchemy import func
        async with self.sessions() as s:
            total = await s.scalar(select(func.count()).select_from(Card).where(Card.user_id == uid))
            due = await s.scalar(select(func.count()).select_from(Card).where(Card.user_id == uid, Card.due <= now()))
            reviews = await s.scalar(select(func.count()).select_from(Review).where(Review.user_id == uid))
            return total, due, reviews

    async def reminder_users(self):
        async with self.sessions() as s:
            return list((await s.scalars(select(User).where(User.reminders.is_(True)))).all())

    async def claim_reminder(self, uid, day):
        async with self.sessions.begin() as s:
            result = await s.execute(update(User).where(User.id == uid, User.reminders.is_(True), User.last_reminder_day != day, User.reminder_lease < now()).values(reminder_lease=now() + 300))
            return result.rowcount == 1

    async def finish_reminder(self, uid, day):
        async with self.sessions.begin() as s:
            await s.execute(update(User).where(User.id == uid).values(last_reminder_day=day, reminder_lease=0))
