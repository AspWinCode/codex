from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth_middleware import get_current_user, require_admin
from app.models.contest import Contest, ContestParticipation, ContestTask
from app.models.user import User
from app.schemas.contest import (
    ContestCreate,
    ContestDetailOut,
    ContestOut,
    ContestTaskOut,
    ContestUpdate,
    LeaderboardEntry,
)

router = APIRouter()


@router.get("", response_model=List[ContestOut])
async def list_contests(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Contest).order_by(Contest.start_at.desc()))
    return [ContestOut.model_validate(c) for c in result.scalars().all()]


@router.get("/{contest_id}", response_model=ContestDetailOut)
async def get_contest(contest_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(
        select(Contest)
        .options(selectinload(Contest.contest_tasks).selectinload(ContestTask.task))
        .where(Contest.id == contest_id)
    )
    contest = result.scalar_one_or_none()
    if contest is None:
        raise HTTPException(status_code=404, detail="Contest not found")
    out = ContestDetailOut.model_validate(contest)
    out.contest_tasks = [
        ContestTaskOut(
            id=ct.id, contest_id=ct.contest_id, task_id=ct.task_id,
            order_index=ct.order_index, max_score=ct.max_score,
            task_title=ct.task.title if ct.task else "",
        )
        for ct in contest.contest_tasks
    ]
    return out


@router.post("", response_model=ContestOut, status_code=status.HTTP_201_CREATED)
async def create_contest(body: ContestCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    contest = Contest(
        title=body.title, description=body.description,
        start_at=body.start_at, end_at=body.end_at,
    )
    db.add(contest)
    await db.flush()
    for ct in body.tasks:
        db.add(ContestTask(contest_id=contest.id, task_id=ct.task_id, order_index=ct.order_index, max_score=ct.max_score))
    await db.flush()
    await db.refresh(contest)
    return ContestOut.model_validate(contest)


@router.put("/{contest_id}", response_model=ContestOut)
async def update_contest(contest_id: int, body: ContestUpdate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(Contest).where(Contest.id == contest_id))
    contest = result.scalar_one_or_none()
    if contest is None:
        raise HTTPException(status_code=404, detail="Contest not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(contest, field, value)
    await db.flush()
    await db.refresh(contest)
    return ContestOut.model_validate(contest)


@router.delete("/{contest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contest(contest_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(Contest).where(Contest.id == contest_id))
    contest = result.scalar_one_or_none()
    if contest is None:
        raise HTTPException(status_code=404, detail="Contest not found")
    await db.delete(contest)


@router.post("/{contest_id}/join", status_code=status.HTTP_201_CREATED)
async def join_contest(contest_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Contest).where(Contest.id == contest_id))
    contest = result.scalar_one_or_none()
    if contest is None:
        raise HTTPException(status_code=404, detail="Contest not found")
    existing = await db.execute(
        select(ContestParticipation).where(
            ContestParticipation.contest_id == contest_id,
            ContestParticipation.user_id == user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already joined")
    db.add(ContestParticipation(contest_id=contest_id, user_id=user.id))
    await db.flush()
    return {"status": "joined"}


@router.get("/{contest_id}/leaderboard", response_model=List[LeaderboardEntry])
async def leaderboard(contest_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(
        select(ContestParticipation)
        .options(selectinload(ContestParticipation.user))
        .where(ContestParticipation.contest_id == contest_id)
        .order_by(ContestParticipation.score.desc(), ContestParticipation.last_ac_at.asc())
    )
    entries = []
    for p in result.scalars().all():
        entries.append(LeaderboardEntry(
            user_id=p.user_id,
            login=p.user.login if p.user else "unknown",
            score=p.score,
            solved_count=p.solved_count,
            last_ac_at=p.last_ac_at,
        ))
    return entries
