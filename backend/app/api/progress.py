from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.student_progress import StudentProgress
from app.models.user import User
from app.schemas.progress import ProgressOut
from app.services.hint_service import get_available_hints
from app.schemas.task import TaskHintOut

router = APIRouter()


@router.get("", response_model=List[ProgressOut])
async def get_progress(
    task_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(StudentProgress).where(StudentProgress.user_id == user.id)
    if task_id is not None:
        q = q.where(StudentProgress.task_id == task_id)
    result = await db.execute(q.order_by(StudentProgress.task_id))
    return [ProgressOut.model_validate(p) for p in result.scalars().all()]


@router.get("/hints/{task_id}", response_model=List[TaskHintOut])
async def get_hints(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await get_available_hints(db, user.id, task_id)
