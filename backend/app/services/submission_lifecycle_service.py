from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.submission import Submission, SubmissionStatus
from app.models.task import Task
from app.schemas.submission import SubmissionExecutionPayload, SubmissionExecutionTest
from app.services.submission_service import enqueue_submission


def _build_execution_payload(submission: Submission, task: Task) -> dict:
    tests = [
        SubmissionExecutionTest(
            id=t.id,
            test_type=t.test_type.value,
            input_data=t.input_data,
            expected_output=t.expected_output,
            verification_sql=t.verification_sql,
            test_files=t.test_files,
            weight=t.weight,
            order_index=t.order_index,
        )
        for t in sorted(task.tests, key=lambda item: item.order_index)
    ]

    payload = SubmissionExecutionPayload(
        submission_id=submission.id,
        user_id=submission.user_id,
        task_id=submission.task_id,
        task_type=task.task_type.value,
        runner_type=task.runner_type.value,
        code=submission.code,
        sql_schema=task.sql_schema,
        sql_seed=task.sql_seed,
        tests=tests,
    )
    return payload.model_dump(mode="json")


async def create_submission_and_enqueue(
    db: AsyncSession,
    *,
    user_id: int,
    task_id: int,
    code: str,
) -> tuple[Submission, str]:
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.tests))
        .where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise ValueError("Task not found")

    submission = Submission(
        task_id=task_id,
        user_id=user_id,
        code=code,
        status=SubmissionStatus.queued,
    )
    db.add(submission)
    await db.flush()

    # Persist before enqueue to avoid a race where judger consumes the task
    # before this transaction is committed.
    await db.commit()
    await db.refresh(submission)

    execution_payload = _build_execution_payload(submission, task)
    enqueue_submission(execution_payload)

    return submission, task.task_type.value
