from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AchievementOut(BaseModel):
    id: int
    code: str
    title: str
    description: str
    icon: str
    points: int

    model_config = {"from_attributes": True}


class UserAchievementOut(BaseModel):
    id: int
    achievement: AchievementOut
    earned_at: datetime

    model_config = {"from_attributes": True}


class ProfileOut(BaseModel):
    user_id: int
    login: str
    role: str
    rating: int
    solved_total: int
    achievements_count: int
    total_points: int
    achievements: list = []
