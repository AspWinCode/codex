from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.gamification import CoinTransaction
from app.models.student_progress import StudentProgress
from app.models.user import User
from app.services.gamification_service import compute_rank, get_or_create_streak, get_or_create_wallet

router = APIRouter()


class GamificationMeOut(BaseModel):
    balance: int
    rank: str
    solved_count: int
    current_streak_days: int
    max_streak_days: int


class CoinTransactionOut(BaseModel):
    id: int
    amount: int
    reason: str
    task_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/me", response_model=GamificationMeOut)
async def get_my_gamification(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    wallet = await get_or_create_wallet(db, user.id)
    streak = await get_or_create_streak(db, user.id)
    solved_result = await db.execute(
        select(func.count()).where(
            StudentProgress.user_id == user.id,
            StudentProgress.best_verdict == "AC",
        )
    )
    solved = solved_result.scalar() or 0
    return GamificationMeOut(
        balance=wallet.balance,
        rank=compute_rank(solved),
        solved_count=solved,
        current_streak_days=streak.current_days,
        max_streak_days=streak.max_days,
    )


@router.get("/transactions", response_model=List[CoinTransactionOut])
async def list_my_transactions(
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CoinTransaction)
        .where(CoinTransaction.user_id == user.id)
        .order_by(CoinTransaction.created_at.desc())
        .limit(limit)
    )
    return [CoinTransactionOut.model_validate(t) for t in result.scalars().all()]
