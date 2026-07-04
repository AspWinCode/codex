from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PersonalLinkCreate(BaseModel):
    task_id: int
    user_id: int
    expires_at: Optional[datetime] = None
    usage_limit: Optional[int] = None


class PersonalLinkOut(BaseModel):
    id: int
    task_id: int
    user_id: int
    token: str
    expires_at: Optional[datetime]
    usage_limit: Optional[int]
    usage_count: int
    url: str = ""

    model_config = {"from_attributes": True}
