from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ProgressOut(BaseModel):
    id: int
    user_id: int
    task_id: int
    attempts: int
    best_verdict: Optional[str]
    solved_at: Optional[datetime]
    last_submission_id: Optional[int]

    model_config = {"from_attributes": True}


class CourseProgressOut(BaseModel):
    course_id: int
    course_title: str
    total_tasks: int
    solved_tasks: int
    attempted_tasks: int
