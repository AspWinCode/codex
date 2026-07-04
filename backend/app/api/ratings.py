from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.rating import RatingHistory, UserRating
from app.models.user import User
from app.schemas.rating import RatingHistoryOut, UserRatingOut

router = APIRouter()


@router.get("/leaderboard", response_model=List[UserRatingOut])
async def leaderboard(limit: int = 50, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    limit = min(limit, 200)
    result = await db.execute(
        select(UserRating)
        .options(selectinload(UserRating.user))
        .order_by(UserRating.rating.desc())
        .limit(limit)
    )
    entries = []
    for r in result.scalars().all():
        entries.append(UserRatingOut(
            user_id=r.user_id,
            login=r.user.login if r.user else "unknown",
            rating=r.rating,
            solved_total=r.solved_total,
            contests_participated=r.contests_participated,
        ))
    return entries


@router.get("/me", response_model=UserRatingOut)
async def my_rating(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(UserRating).where(UserRating.user_id == user.id))
    rating = result.scalar_one_or_none()
    if rating is None:
        return UserRatingOut(user_id=user.id, login=user.login, rating=1200, solved_total=0, contests_participated=0)
    return UserRatingOut(
        user_id=rating.user_id, login=user.login, rating=rating.rating,
        solved_total=rating.solved_total, contests_participated=rating.contests_participated,
    )


@router.get("/history/{user_id}", response_model=List[RatingHistoryOut])
async def rating_history(user_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(
        select(RatingHistory).where(RatingHistory.user_id == user_id).order_by(RatingHistory.created_at.desc()).limit(50)
    )
    return [RatingHistoryOut.model_validate(r) for r in result.scalars().all()]
