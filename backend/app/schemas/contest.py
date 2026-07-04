from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.models.contest import ContestStatus


class ContestTaskCreate(BaseModel):
    task_id: int
    order_index: int = 0
    max_score: int = 100


class ContestTaskOut(BaseModel):
    id: int
    contest_id: int
    task_id: int
    order_index: int
    max_score: int
    task_title: str = ""

    model_config = {"from_attributes": True}


class ContestCreate(BaseModel):
    title: str
    description: Optional[str] = None
    start_at: datetime
    end_at: datetime
    tasks: List[ContestTaskCreate] = []


class ContestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ContestStatus] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None


class ContestOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: ContestStatus
    start_at: datetime
    end_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class ContestDetailOut(ContestOut):
    contest_tasks: List[ContestTaskOut] = []


class LeaderboardEntry(BaseModel):
    user_id: int
    login: str
    score: int
    solved_count: int
    last_ac_at: Optional[datetime]
