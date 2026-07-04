from __future__ import annotations

from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student_progress import StudentProgress
from app.models.submission import Submission, SubmissionStatus, Verdict
from app.models.submission_test import SubmissionTest
from app.models.task import Task
from app.schemas.submission import SubmissionCompleteIn
from app.services.course_progress_service import mark_task_completed_in_courses
from app.services.gamification_service import award_coins, bump_streak
from app.services.progress_service import update_progress


async def get_submission(db: AsyncSession, submission_id: int) -> Optional[Submission]:
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    return result.scalar_one_or_none()


async def mark_submission_running(db: AsyncSession, submission_id: int) -> Optional[Submission]:
    submission = await get_submission(db, submission_id)
    if submission is None:
        return None
    if submission.status != SubmissionStatus.finished:
        submission.status = SubmissionStatus.running
        await db.flush()
    return submission


async def finalize_submission(db: AsyncSession, submission: Submission, body: SubmissionCompleteIn) -> None:
    if submission.status == SubmissionStatus.finished and submission.verdict is not None:
        return

    submission.status = SubmissionStatus.finished
    submission.verdict = body.verdict
    submission.runtime = body.runtime
    submission.memory = body.memory
    submission.error_output = body.error_output

    await db.execute(delete(SubmissionTest).where(SubmissionTest.submission_id == submission.id))

    # Захватываем состояние ДО update_progress — иначе не отличить первое решение от пересдачи
    prior_progress = await db.execute(
        select(StudentProgress).where(
            StudentProgress.user_id == submission.user_id,
            StudentProgress.task_id == submission.task_id,
        )
    )
    prior = prior_progress.scalar_one_or_none()
    was_already_solved = prior is not None and prior.solved_at is not None
    was_first_attempt = prior is None or prior.attempts == 0

    for tr in body.test_results:
        db.add(
            SubmissionTest(
                submission_id=submission.id,
                test_id=tr.test_id,
                verdict=tr.verdict,
                runtime=tr.runtime,
                actual_output=tr.actual_output,
            )
        )

    await update_progress(
        db,
        user_id=submission.user_id,
        task_id=submission.task_id,
        submission_id=submission.id,
        verdict=body.verdict.value,
    )
    # Если решение успешное, обновляем прогресс по курсам/узлам
    if body.verdict == Verdict.AC:
        await mark_task_completed_in_courses(
            db,
            user_id=submission.user_id,
            task_id=submission.task_id,
            submission_id=submission.id,
        )
        # Монеты начисляются один раз за задачу — при первом решении, не при пересдаче
        if not was_already_solved:
            task_result = await db.execute(select(Task).where(Task.id == submission.task_id))
            task = task_result.scalar_one_or_none()
            base_reward = task.reward_coins if task else 10
            if was_first_attempt:
                base_reward = round(base_reward * 1.2)  # бонус +20% за решение с первой попытки
            await award_coins(db, submission.user_id, base_reward, reason="task_solved", task_id=submission.task_id)
            await bump_streak(db, submission.user_id)
    await db.flush()
