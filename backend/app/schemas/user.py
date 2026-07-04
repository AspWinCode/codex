from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole, UserStatus


class UserCreate(BaseModel):
    login: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(..., min_length=4, max_length=128)
    role: UserRole = UserRole.student
    email: Optional[str] = None
    full_name: Optional[str] = None


class UserUpdate(BaseModel):
    login: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    email: Optional[str] = None
    full_name: Optional[str] = None


class UserOut(BaseModel):
    id: int
    login: str
    role: UserRole
    status: UserStatus
    email: Optional[str] = None
    full_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResetPassword(BaseModel):
    new_password: str = Field(..., min_length=4, max_length=128)


class ChangePassword(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=4, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordByToken(BaseModel):
    token: str
    new_password: str = Field(..., min_length=4, max_length=128)
