from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import settings
from app.database import Base, get_engine, get_session_factory
from app.logging_config import setup_logging

setup_logging()
from app.models.password_reset_token import PasswordResetToken  # noqa: F401
from app.models.user import User, UserRole, UserStatus
from app.services.auth_service import hash_password


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = get_engine()
    if settings.AUTO_CREATE_TABLES:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    session_factory = get_session_factory()
    async with session_factory() as db:
        result = await db.execute(select(User).where(User.login == settings.ADMIN_LOGIN))
        if result.scalar_one_or_none() is None:
            admin = User(
                login=settings.ADMIN_LOGIN,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                role=UserRole.admin,
                status=UserStatus.active,
            )
            db.add(admin)
            await db.commit()

    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(title="Kodex", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.middleware.error_handler import register_error_handlers  # noqa: E402
register_error_handlers(app)

from app.api import auth  # noqa: E402

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])


@app.get("/api/health")
async def health():
    import redis as sync_redis

    checks = {"db": "ok", "redis": "ok"}
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(select(User).limit(1))
    except Exception as e:
        checks["db"] = str(e)
    try:
        r = sync_redis.from_url(settings.REDIS_URL)
        r.ping()
        r.close()
    except Exception as e:
        checks["redis"] = str(e)
    healthy = all(v == "ok" for v in checks.values())
    return {"status": "ok" if healthy else "degraded", "checks": checks}
