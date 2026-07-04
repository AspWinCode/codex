from __future__ import annotations

from pydantic import BaseModel

from app.schemas.user import UserOut


class LoginRequest(BaseModel):
    login: str
    password: str


class TokenResponse(BaseModel):
    token: str
    refresh_token: str
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    token: str
    refresh_token: str
