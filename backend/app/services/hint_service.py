from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gamification import StudentHintUnlock
from app.models.student_progress import StudentProgress
from app.models.task_hint import TaskHint
from app.schemas.task import TaskHintOut


async def get_available_hints(db: AsyncSession, user_id: int, task_id: int) -> List[TaskHintOut]:
    """Подсказка становится доступна к ПОКУПКЕ после нужного числа попыток
    (unlock_attempts), но содержимое отдаётся только после покупки за монеты
    (см. POST /api/tasks/hints/{id}/unlock). Непроданные подсказки возвращаются
    с content=None, чтобы фронт мог показать кнопку «Купить за N монет».

    Важно: мутируем поле content только на Pydantic-копии (TaskHintOut), а не
    на живом ORM-объекте TaskHint — иначе SQLAlchemy может случайно записать
    None в базу при следующем flush/commit в рамках этого запроса."""
    prog_result = await db.execute(
        select(StudentProgress).where(
            StudentProgress.user_id == user_id,
            StudentProgress.task_id == task_id,
        )
    )
    progress = prog_result.scalar_one_or_none()
    attempts = progress.attempts if progress else 0

    hints_result = await db.execute(
        select(TaskHint)
        .where(TaskHint.task_id == task_id, TaskHint.unlock_attempts <= attempts)
        .order_by(TaskHint.hint_level)
    )
    hints = list(hints_result.scalars().all())
    if not hints:
        return []

    unlocked_result = await db.execute(
        select(StudentHintUnlock.hint_id).where(
            StudentHintUnlock.user_id == user_id,
            StudentHintUnlock.hint_id.in_([h.id for h in hints]),
        )
    )
    unlocked_ids = {row[0] for row in unlocked_result.all()}

    out: List[TaskHintOut] = []
    for hint in hints:
        item = TaskHintOut.model_validate(hint)
        item.is_unlocked = hint.id in unlocked_ids
        if not item.is_unlocked:
            item.content = None
        out.append(item)

    return out
