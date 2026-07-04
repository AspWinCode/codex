"""Platform settings endpoints – logo upload, etc."""
from __future__ import annotations

import base64
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth_middleware import get_current_user, require_admin
from app.models.platform_settings import PlatformSetting
from app.models.user import User

router = APIRouter()

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/svg+xml", "image/webp", "image/gif"}
MAX_SIZE = 2 * 1024 * 1024  # 2 MB


@router.get("/settings/logo")
async def get_logo(db: AsyncSession = Depends(get_db)):
    """Public – returns {url: "data:image/..."} or {url: null}."""
    result = await db.execute(
        select(PlatformSetting).where(PlatformSetting.key == "logo")
    )
    row = result.scalar_one_or_none()
    return {"url": row.value if row and row.value else None}


@router.post("/settings/logo")
async def upload_logo(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Admin-only – upload a logo image. Stored as base64 data-URI."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Недопустимый тип файла: {file.content_type}")

    data = await file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(400, "Файл слишком большой (макс. 2 МБ)")

    b64 = base64.b64encode(data).decode()
    data_uri = f"data:{file.content_type};base64,{b64}"

    result = await db.execute(
        select(PlatformSetting).where(PlatformSetting.key == "logo")
    )
    row = result.scalar_one_or_none()
    if row:
        row.value = data_uri
    else:
        db.add(PlatformSetting(key="logo", value=data_uri))

    await db.commit()
    return {"url": data_uri}


@router.delete("/settings/logo")
async def delete_logo(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Admin-only – remove logo."""
    result = await db.execute(
        select(PlatformSetting).where(PlatformSetting.key == "logo")
    )
    row = result.scalar_one_or_none()
    if row:
        row.value = ""
        await db.commit()
    return {"url": None}
