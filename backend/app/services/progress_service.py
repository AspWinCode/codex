from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student_progress import StudentProgress
from app.models.submission import Verdict


async def update_progress(db: AsyncSession, user_id: int, task_id: int, submission_id: int, verdict: str):
    result = await db.execute(
        select(StudentProgress).where(
            StudentProgress.user_id == user_id,
            StudentProgress.task_id == task_id,
        )
    )
    progress = result.scalar_one_or_none()
    if progress is None:
        progress = StudentProgress(user_id=user_id, task_id=task_id, attempts=0)
        db.add(progress)
    progress.attempts += 1
    progress.last_submission_id = submission_id
    verdict_priority = {Verdict.AC.value: 10}
    current_priority = verdict_priority.get(progress.best_verdict, 0)
    new_priority = verdict_priority.get(verdict, 0)
    if new_priority > current_priority:
        progress.best_verdict = verdict
    if verdict == Verdict.AC.value and progress.solved_at is None:
        progress.solved_at = datetime.now(timezone.utc)
    await db.flush()
