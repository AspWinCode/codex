from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.models.task import RunnerType, TaskStatus, TaskType
from app.models.task_test import TestType


class TaskTestCreate(BaseModel):
    test_type: TestType = TestType.public
    input_data: Optional[str] = None
    expected_output: Optional[str] = None
    verification_sql: Optional[str] = None
    test_files: Optional[List] = None  # [{"name": "data.csv", "content": "..."}]
    weight: float = 1.0
    order_index: int = 0


class TaskTestOut(BaseModel):
    id: int
    task_id: int
    test_type: TestType
    input_data: Optional[str]
    expected_output: Optional[str]
    verification_sql: Optional[str]
    test_files: Optional[List]
    weight: float
    order_index: int

    model_config = {"from_attributes": True}


class TaskHintCreate(BaseModel):
    hint_level: int = 1
    unlock_attempts: int = 3
    coin_cost: int = 30
    content: str


class TaskHintOut(BaseModel):
    id: int
    task_id: int
    hint_level: int
    unlock_attempts: int
    coin_cost: int
    content: Optional[str] = None
    is_unlocked: bool = True

    model_config = {"from_attributes": True}


class TaskLectureCreate(BaseModel):
    content: str
    unlock_attempts: int = 0


class TaskLectureOut(BaseModel):
    id: int
    task_id: int
    content: str
    unlock_attempts: int

    model_config = {"from_attributes": True}


class TaskCreate(BaseModel):
    submodule_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    task_type: TaskType
    runner_type: RunnerType
    status: TaskStatus = TaskStatus.draft
    reward_coins: int = 10
    sql_schema: Optional[str] = None
    sql_seed: Optional[str] = None
    tests: List[TaskTestCreate] = []
    hints: List[TaskHintCreate] = []
    lectures: List[TaskLectureCreate] = []


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    submodule_id: Optional[int] = None
    task_type: Optional[TaskType] = None
    runner_type: Optional[RunnerType] = None
    status: Optional[TaskStatus] = None
    reward_coins: Optional[int] = None
    sql_schema: Optional[str] = None
    sql_seed: Optional[str] = None


class TaskOut(BaseModel):
    id: int
    submodule_id: Optional[int]
    title: str
    description: Optional[str]
    task_type: TaskType
    runner_type: RunnerType
    status: TaskStatus
    version: int
    reward_coins: int = 10
    sql_schema: Optional[str] = None
    sql_seed: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskDetailOut(TaskOut):
    tests: List[TaskTestOut] = []
    hints: List[TaskHintOut] = []
    lectures: List[TaskLectureOut] = []
