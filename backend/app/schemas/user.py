from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class UserOut(BaseModel):
    id: int
    login: str
    role: str
    full_name: Optional[str] = None

    model_config = {"from_attributes": True}


class ChangePassword(BaseModel):
    old_password: str
    new_password: str
