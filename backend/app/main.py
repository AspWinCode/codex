from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import settings
from app.database import Base, get_engine, get_session_factory
from app.logging_config import setup_logging

setup_logging()
from app.models.password_reset_token import PasswordResetToken  # noqa: F401 — register model
from app.models.user import User, UserRole, UserStatus
from app.services.auth_service import hash_password


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = get_engine()
    # Schema is managed by Alembic (entrypoint.sh runs `alembic upgrade head`).
    # Fallback create_all for local dev without Alembic:
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

    from app.api.ws import start_submission_event_listener

    start_submission_event_listener()
    try:
        yield
    finally:
        from app.api.ws import stop_submission_event_listener

        await stop_submission_event_listener()
        await engine.dispose()


app = FastAPI(title="ITPractikum", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.middleware.prometheus import setup_prometheus  # noqa: E402
setup_prometheus(app)

from app.middleware.error_handler import register_error_handlers  # noqa: E402
register_error_handlers(app)

from app.api import auth, users, courses, tasks, submissions, progress, personal_links  # noqa: E402
from app.api import ws, contests, ratings, achievements  # noqa: E402
from app.api import admin_courses, course_student, platform_settings  # noqa: E402
from app.api import getcourse  # noqa: E402
from app.api import gamification  # noqa: E402

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(admin_courses.router, prefix="/api", tags=["Admin Courses"])
app.include_router(course_student.router, prefix="/api", tags=["Course Student"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(courses.router, prefix="/api/courses", tags=["Courses"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(submissions.router, prefix="/api/submissions", tags=["Submissions"])
app.include_router(progress.router, prefix="/api/progress", tags=["Progress"])
app.include_router(personal_links.router, prefix="/api/personal-links", tags=["Personal Links"])
app.include_router(contests.router, prefix="/api/contests", tags=["Contests"])
app.include_router(ratings.router, prefix="/api/ratings", tags=["Ratings"])
app.include_router(achievements.router, prefix="/api/achievements", tags=["Achievements"])
app.include_router(ws.router, prefix="/api/ws", tags=["WebSocket"])
app.include_router(platform_settings.router, prefix="/api", tags=["Platform Settings"])
app.include_router(getcourse.router, prefix="/api/getcourse", tags=["GetCourse"])
app.include_router(gamification.router, prefix="/api/gamification", tags=["Gamification"])


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
