from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth_middleware import get_current_user, require_admin
from app.models.personal_link import PersonalLink
from app.models.task import Task
from app.models.user import User
from app.schemas.personal_link import PersonalLinkCreate, PersonalLinkOut
from app.schemas.task import TaskDetailOut
from app.services.link_service import generate_token
from sqlalchemy.orm import selectinload

router = APIRouter()


@router.post("", response_model=PersonalLinkOut, status_code=status.HTTP_201_CREATED)
async def create_link(body: PersonalLinkCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    token = generate_token(body.task_id, body.user_id)
    link = PersonalLink(
        task_id=body.task_id,
        user_id=body.user_id,
        token=token,
        expires_at=body.expires_at,
        usage_limit=body.usage_limit,
    )
    db.add(link)
    await db.flush()
    await db.refresh(link)
    out = PersonalLinkOut.model_validate(link)
    out.url = f"/shared/{token}"
    return out


@router.get("", response_model=List[PersonalLinkOut])
async def list_links(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(PersonalLink).order_by(PersonalLink.id))
    links = []
    for link in result.scalars().all():
        out = PersonalLinkOut.model_validate(link)
        out.url = f"/shared/{link.token}"
        links.append(out)
    return links


@router.get("/resolve/{token}", response_model=TaskDetailOut)
async def resolve_link(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PersonalLink).where(PersonalLink.token == token))
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=404, detail="Link not found")
    if link.expires_at and link.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Link expired")
    if link.usage_limit and link.usage_count >= link.usage_limit:
        raise HTTPException(status_code=410, detail="Link usage limit reached")
    link.usage_count += 1
    task_result = await db.execute(
        select(Task)
        .options(selectinload(Task.tests), selectinload(Task.hints), selectinload(Task.lectures))
        .where(Task.id == link.task_id)
    )
    task = task_result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    out = TaskDetailOut.model_validate(task)
    # Personal links are unauthenticated — never expose expected answers or test internals
    for test in out.tests:
        test.expected_output = None
        test.verification_sql = None
        test.test_files = None
    return out
