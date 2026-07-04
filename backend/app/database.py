from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


_engine = None
_async_session = None


def get_engine():
    global _engine
    if _engine is None:
        from app.config import settings
        _engine = create_async_engine(settings.DATABASE_URL, echo=False)
    return _engine


def get_session_factory():
    global _async_session
    if _async_session is None:
        _async_session = async_sessionmaker(get_engine(), class_=AsyncSession, expire_on_commit=False)
    return _async_session


def set_engine_and_session(eng, sess):
    """Used by test fixtures to inject an in-memory database."""
    global _engine, _async_session
    _engine = eng
    _async_session = sess


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
