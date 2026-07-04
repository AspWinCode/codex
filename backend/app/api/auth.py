from __future__ import annotations

import base64
import json
import secrets
import time
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User, UserRole, UserStatus
from app.schemas.auth import LoginRequest, RefreshRequest, RefreshResponse, TokenResponse
from app.schemas.user import ChangePassword, UserOut
from app.services.auth_service import (
    consume_sso_jti,
    create_token_pair,
    decode_refresh_token,
    decode_sso_token,
    hash_password,
    verify_password,
)

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.login == body.login))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if user.status != UserStatus.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active")
    access, refresh = create_token_pair(user.id, user.role.value)
    return TokenResponse(token=access, refresh_token=refresh, user=UserOut.model_validate(user))


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_refresh_token(body.refresh_token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None or user.status != UserStatus.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or blocked")
    access, refresh = create_token_pair(user.id, user.role.value)
    return RefreshResponse(token=access, refresh_token=refresh)


@router.get("/sso")
async def sso_login(token: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Вход по SSO-токену от learning-portal (tirskix.space). Find-or-create ученика,
    выдаёт обычную сессию платформы и редиректит в SPA с токенами во fragment'е URL
    (не в query — чтобы они не осели в access-логах)."""
    payload = decode_sso_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired SSO token")

    external_ref = str(payload.get("external_ref") or "").strip()
    full_name = str(payload.get("full_name") or "").strip() or None
    jti = str(payload.get("jti") or "").strip()
    exp = int(payload.get("exp") or 0)
    if not external_ref or not jti:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid SSO token payload")

    ttl = max(exp - int(time.time()), 1)
    if not consume_sso_jti(jti, ttl):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="SSO token already used")

    result = await db.execute(select(User).where(User.login == external_ref))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            login=external_ref,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            role=UserRole.student,
            status=UserStatus.active,
            full_name=full_name,
        )
        db.add(user)
        await db.flush()
    elif user.status != UserStatus.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active")

    access, refresh = create_token_pair(user.id, user.role.value)
    user_json = UserOut.model_validate(user).model_dump_json()
    user_b64 = base64.urlsafe_b64encode(user_json.encode("utf-8")).decode("ascii")
    redirect_url = (
        f"{settings.FRONTEND_URL}/#access_token={quote(access)}"
        f"&refresh_token={quote(refresh)}&user={quote(user_b64)}"
    )
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)


@router.post("/change-password")
async def change_password(
    body: ChangePassword,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Неверный текущий пароль")
    user.password_hash = hash_password(body.new_password)
    await db.flush()
    return {"detail": "Пароль успешно изменён"}
