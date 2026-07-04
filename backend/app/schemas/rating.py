from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserRatingOut(BaseModel):
    user_id: int
    login: str
    rating: int
    solved_total: int
    contests_participated: int

    model_config = {"from_attributes": True}


class RatingHistoryOut(BaseModel):
    id: int
    old_rating: int
    new_rating: int
    reason: str
    created_at: datetime

    model_config = {"from_attributes": True}
