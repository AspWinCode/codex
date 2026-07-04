from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth_middleware import get_current_user, require_admin
from app.models.achievement import Achievement, UserAchievement
from app.models.rating import UserRating
from app.models.user import User
from app.schemas.achievement import AchievementOut, ProfileOut, UserAchievementOut

router = APIRouter()


@router.get("", response_model=List[AchievementOut])
async def list_achievements(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Achievement).order_by(Achievement.id))
    return [AchievementOut.model_validate(a) for a in result.scalars().all()]


@router.get("/my", response_model=List[UserAchievementOut])
async def my_achievements(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(
        select(UserAchievement)
        .options(selectinload(UserAchievement.achievement))
        .where(UserAchievement.user_id == user.id)
        .order_by(UserAchievement.earned_at.desc())
    )
    return [UserAchievementOut.model_validate(ua) for ua in result.scalars().all()]


@router.get("/profile/{user_id}", response_model=ProfileOut)
async def user_profile(user_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    rating_result = await db.execute(select(UserRating).where(UserRating.user_id == user_id))
    rating = rating_result.scalar_one_or_none()

    achievements_result = await db.execute(
        select(UserAchievement)
        .options(selectinload(UserAchievement.achievement))
        .where(UserAchievement.user_id == user_id)
        .order_by(UserAchievement.earned_at.desc())
    )
    user_achievements = achievements_result.scalars().all()

    total_points = sum(ua.achievement.points for ua in user_achievements if ua.achievement)
    achievements = [
        {"code": ua.achievement.code, "title": ua.achievement.title, "icon": ua.achievement.icon, "earned_at": str(ua.earned_at)}
        for ua in user_achievements if ua.achievement
    ]

    return ProfileOut(
        user_id=user.id,
        login=user.login,
        role=user.role.value,
        rating=rating.rating if rating else 1200,
        solved_total=rating.solved_total if rating else 0,
        achievements_count=len(user_achievements),
        total_points=total_points,
        achievements=achievements,
    )


@router.post("/seed", status_code=201)
async def seed_achievements(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    """Seed default achievements into the database."""
    defaults = [
        ("first_solve", "First Blood", "Solve your first task", "trophy", 10),
        ("ten_solves", "Getting Started", "Solve 10 tasks", "fire", 25),
        ("fifty_solves", "Problem Crusher", "Solve 50 tasks", "rocket", 50),
        ("hundred_solves", "Centurion", "Solve 100 tasks", "crown", 100),
        ("all_types", "Polyglot", "Solve tasks of all types", "globe", 30),
        ("speed_demon", "Speed Demon", "Solve a task in under 0.1s", "bolt", 15),
        ("streak_5", "On Fire", "5 correct submissions in a row", "flame", 20),
        ("streak_10", "Unstoppable", "10 correct submissions in a row", "star", 40),
        ("first_contest", "Competitor", "Participate in a contest", "flag", 15),
        ("contest_top3", "Podium Finish", "Finish in top 3 of a contest", "medal", 50),
    ]
    count = 0
    for code, title, desc, icon, pts in defaults:
        existing = await db.execute(select(Achievement).where(Achievement.code == code))
        if existing.scalar_one_or_none() is None:
            db.add(Achievement(code=code, title=title, description=desc, icon=icon, points=pts))
            count += 1
    await db.flush()
    return {"seeded": count}
