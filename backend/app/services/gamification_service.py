from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.achievement import Achievement, UserAchievement
from app.models.gamification import CoinTransaction, CoinWallet, StudentStreak
from app.models.rating import UserRating
from app.models.student_progress import StudentProgress

log = logging.getLogger(__name__)


async def _award(db: AsyncSession, user_id: int, code: str):
    existing = await db.execute(
        select(UserAchievement)
        .join(Achievement)
        .where(UserAchievement.user_id == user_id, Achievement.code == code)
    )
    if existing.scalar_one_or_none():
        return
    ach = await db.execute(select(Achievement).where(Achievement.code == code))
    achievement = ach.scalar_one_or_none()
    if achievement is None:
        return
    db.add(UserAchievement(user_id=user_id, achievement_id=achievement.id))
    log.info("Awarded achievement '%s' to user %d", code, user_id)


async def check_achievements(db: AsyncSession, user_id: int):
    """Check and award achievements based on current progress."""
    solved_result = await db.execute(
        select(func.count()).where(
            StudentProgress.user_id == user_id,
            StudentProgress.best_verdict == "AC",
        )
    )
    solved = solved_result.scalar() or 0

    if solved >= 1:
        await _award(db, user_id, "first_solve")
    if solved >= 10:
        await _award(db, user_id, "ten_solves")
    if solved >= 50:
        await _award(db, user_id, "fifty_solves")
    if solved >= 100:
        await _award(db, user_id, "hundred_solves")

    rating_result = await db.execute(select(UserRating).where(UserRating.user_id == user_id))
    rating = rating_result.scalar_one_or_none()
    if rating is None:
        rating = UserRating(user_id=user_id, rating=1200)
        db.add(rating)
    rating.solved_total = solved
    await db.flush()


async def update_rating_on_solve(db: AsyncSession, user_id: int):
    """Simple rating bump on solve (+5 per solve)."""
    result = await db.execute(select(UserRating).where(UserRating.user_id == user_id))
    rating = result.scalar_one_or_none()
    if rating is None:
        rating = UserRating(user_id=user_id, rating=1200)
        db.add(rating)
        await db.flush()
    rating.rating += 5
    await db.flush()


# ─── Монеты, стрики и ранг (Кодэкс) ──────────────────────────────────────────

STREAK_BONUS_EVERY_DAYS = 7
STREAK_BONUS_COINS = 50

# Пороги ранга по числу решённых задач (см. концепцию «Кодэкс» — ранги агентства).
RANKS = [
    (0, "Стажёр"),
    (3, "Агент"),
    (7, "Инспектор"),
    (12, "Детектив"),
    (20, "Шеф"),
]


def compute_rank(solved_count: int) -> str:
    current = RANKS[0][1]
    for threshold, name in RANKS:
        if solved_count >= threshold:
            current = name
    return current


async def get_or_create_wallet(db: AsyncSession, user_id: int) -> CoinWallet:
    result = await db.execute(select(CoinWallet).where(CoinWallet.user_id == user_id))
    wallet = result.scalar_one_or_none()
    if wallet is None:
        wallet = CoinWallet(user_id=user_id, balance=0)
        db.add(wallet)
        await db.flush()
    return wallet


async def award_coins(db: AsyncSession, user_id: int, amount: int, reason: str, task_id: int | None = None) -> CoinWallet:
    if amount == 0:
        return await get_or_create_wallet(db, user_id)
    wallet = await get_or_create_wallet(db, user_id)
    wallet.balance += amount
    db.add(CoinTransaction(user_id=user_id, amount=amount, reason=reason, task_id=task_id))
    await db.flush()
    return wallet


async def spend_coins(db: AsyncSession, user_id: int, amount: int, reason: str, task_id: int | None = None) -> bool:
    """Списывает монеты, если баланса достаточно. Возвращает False при нехватке средств."""
    wallet = await get_or_create_wallet(db, user_id)
    if wallet.balance < amount:
        return False
    wallet.balance -= amount
    db.add(CoinTransaction(user_id=user_id, amount=-amount, reason=reason, task_id=task_id))
    await db.flush()
    return True


async def get_or_create_streak(db: AsyncSession, user_id: int) -> StudentStreak:
    result = await db.execute(select(StudentStreak).where(StudentStreak.user_id == user_id))
    streak = result.scalar_one_or_none()
    if streak is None:
        streak = StudentStreak(user_id=user_id, current_days=0, max_days=0, last_active_date=None)
        db.add(streak)
        await db.flush()
    return streak


async def bump_streak(db: AsyncSession, user_id: int) -> StudentStreak:
    """Отмечает активность за сегодня. Идемпотентно в рамках одного дня."""
    today = datetime.now(timezone.utc).date()
    streak = await get_or_create_streak(db, user_id)

    if streak.last_active_date == today:
        return streak

    if streak.last_active_date == today - timedelta(days=1):
        streak.current_days += 1
    else:
        streak.current_days = 1

    streak.max_days = max(streak.max_days, streak.current_days)
    streak.last_active_date = today
    await db.flush()

    if streak.current_days > 0 and streak.current_days % STREAK_BONUS_EVERY_DAYS == 0:
        await award_coins(db, user_id, STREAK_BONUS_COINS, reason="streak_bonus")

    return streak
