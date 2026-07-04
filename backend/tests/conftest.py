from __future__ import annotations

import os
from typing import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Required settings for backend/app/config.py in tests
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ADMIN_PASSWORD", "admin123")
os.environ.setdefault("JUDGER_INTERNAL_TOKEN", "test-judger-internal-token")
os.environ.setdefault("CORS_ORIGINS", "http://test")

TEST_DATABASE_URL = "sqlite+aiosqlite://"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)

from app.database import Base, get_db, set_engine_and_session  # noqa: E402

TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
set_engine_and_session(test_engine, TestSession)

from app.main import app  # noqa: E402
from app.models import *  # noqa: E402, F401, F403
from app.services.auth_service import create_access_token, hash_password  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_connection() -> AsyncGenerator[AsyncConnection, None]:
    async with test_engine.connect() as connection:
        yield connection


@pytest_asyncio.fixture
async def db(db_connection: AsyncConnection) -> AsyncGenerator[AsyncSession, None]:
    transaction = await db_connection.begin()
    session = AsyncSession(bind=db_connection, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        if transaction.is_active:
            await transaction.rollback()


@pytest_asyncio.fixture(autouse=True)
async def override_get_db(db: AsyncSession):
    """Make the FastAPI dependency use the same session as the test fixtures."""

    async def _get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db

    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession):
    from app.models.user import User, UserRole, UserStatus

    user = User(login="admin", password_hash=hash_password("admin123"), role=UserRole.admin, status=UserStatus.active)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def student_user(db: AsyncSession):
    from app.models.user import User, UserRole, UserStatus

    user = User(login="student1", password_hash=hash_password("pass123"), role=UserRole.student, status=UserStatus.active)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
def admin_headers(admin_user):
    token = create_access_token({"sub": str(admin_user.id), "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
def student_headers(student_user):
    token = create_access_token({"sub": str(student_user.id), "role": "student"})
    return {"Authorization": f"Bearer {token}"}