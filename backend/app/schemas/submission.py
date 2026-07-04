from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.submission import SubmissionStatus, Verdict
from app.models.task_test import TestType


class SubmissionCreate(BaseModel):
    task_id: int
    code: str = Field(..., min_length=1, max_length=100_000)


class SubmissionOut(BaseModel):
    id: int
    task_id: int
    user_id: int
    code: str
    status: SubmissionStatus
    verdict: Optional[Verdict]
    runtime: Optional[float]
    memory: Optional[float]
    error_output: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class SubmissionTestOut(BaseModel):
    id: int
    test_id: int
    verdict: Optional[Verdict]
    runtime: Optional[float]
    actual_output: Optional[str]
    test_type: Optional[TestType] = None
    input_data: Optional[str] = None
    expected_output: Optional[str] = None

    model_config = {"from_attributes": True}


class SubmissionDetailOut(SubmissionOut):
    test_results: List[SubmissionTestOut] = []


class SubmissionExecutionTest(BaseModel):
    id: int
    test_type: str
    input_data: Optional[str] = None
    expected_output: Optional[str] = None
    verification_sql: Optional[str] = None
    test_files: Optional[List] = None  # [{"name": "data.csv", "content": "..."}]
    weight: float = 1.0
    order_index: int = 0


class SubmissionExecutionPayload(BaseModel):
    submission_id: int
    user_id: int
    task_id: int
    task_type: str
    runner_type: str
    code: str
    sql_schema: Optional[str] = None
    sql_seed: Optional[str] = None
    tests: List[SubmissionExecutionTest] = []


class SubmissionTestResultIn(BaseModel):
    test_id: int
    verdict: Verdict
    runtime: Optional[float] = None
    actual_output: Optional[str] = None


class SubmissionCompleteIn(BaseModel):
    verdict: Verdict
    runtime: Optional[float] = None
    memory: Optional[float] = None
    error_output: Optional[str] = None
    test_results: List[SubmissionTestResultIn] = []
