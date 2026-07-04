from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course import Course, CourseStatus
from app.models.course_node import CourseNode, CourseNodeStatus
from app.models.course_node_task import CourseNodeTask
from app.models.submission import Verdict
from app.models.user_course_node_task_progress import (
    NodeTaskProgressStatus,
    UserCourseNodeTaskProgress,
)
from app.models.user_course_progress import UserCourseProgress


async def mark_task_completed_in_courses(
    db: AsyncSession,
    *,
    user_id: int,
    task_id: int,
    submission_id: int,
) -> None:
    """Отметить задачу как завершённую во всех курсах, где она прикреплена.

    Вызывается после успешного решения (AC).
    """
    r = await db.execute(
        select(CourseNodeTask)
        .options(
            selectinload(CourseNodeTask.node).selectinload(CourseNode.course),
            selectinload(CourseNodeTask.node).selectinload(CourseNode.children),
        )
        .where(CourseNodeTask.task_id == task_id)
    )
    node_tasks: list[CourseNodeTask] = r.scalars().all()
    if not node_tasks:
        return

    now = datetime.now(timezone.utc)

    affected_course_ids: set[int] = set()

    for nt in node_tasks:
        node = nt.node
        course = node.course
        if not course or course.status != CourseStatus.published:
            continue
        # Узел должен быть опубликован и конечным
        if node.status != CourseNodeStatus.published or node.children:
            continue

        affected_course_ids.add(course.id)

        r_prog = await db.execute(
            select(UserCourseNodeTaskProgress).where(
                UserCourseNodeTaskProgress.user_id == user_id,
                UserCourseNodeTaskProgress.node_task_id == nt.id,
            )
        )
        prog = r_prog.scalar_one_or_none()
        if prog is None:
            prog = UserCourseNodeTaskProgress(
                user_id=user_id,
                node_task_id=nt.id,
                status=NodeTaskProgressStatus.completed,
                best_submission_id=submission_id,
                completed_at=now,
            )
            db.add(prog)
        else:
            # Если уже completed, не понижаем статус
            prog.status = NodeTaskProgressStatus.completed
            prog.best_submission_id = submission_id
            prog.completed_at = prog.completed_at or now

    for course_id in affected_course_ids:
        await recalculate_course_progress(db, user_id=user_id, course_id=course_id)


async def recalculate_course_progress(
    db: AsyncSession,
    *,
    user_id: int,
    course_id: int,
) -> None:
    """Пересчитать UserCourseProgress для пользователя по курсу."""
    r_course = await db.execute(select(Course).where(Course.id == course_id))
    course = r_course.scalar_one_or_none()
    if not course or course.status != CourseStatus.published:
        return

    # Находим все опубликованные конечные узлы курса
    r_nodes = await db.execute(
        select(CourseNode)
        .options(selectinload(CourseNode.children))
        .where(
            CourseNode.course_id == course_id,
            CourseNode.status == CourseNodeStatus.published,
        )
    )
    nodes: list[CourseNode] = r_nodes.scalars().all()
    leaf_node_ids = [n.id for n in nodes if not n.children]
    if not leaf_node_ids:
        total_tasks_count = 0
    else:
        r_total = await db.execute(
            select(func.count(CourseNodeTask.id)).where(
                CourseNodeTask.node_id.in_(leaf_node_ids),
            )
        )
        total_tasks_count = int(r_total.scalar() or 0)

    if total_tasks_count == 0:
        completed_tasks_count = 0
        progress_percent = 0.0
    else:
        # Находим все node_tasks по этим leaf-узлам
        r_node_tasks = await db.execute(
            select(CourseNodeTask.id).where(
                CourseNodeTask.node_id.in_(leaf_node_ids),
            )
        )
        node_task_ids: Iterable[int] = [row[0] for row in r_node_tasks.fetchall()]
        if not node_task_ids:
            completed_tasks_count = 0
            progress_percent = 0.0
        else:
            r_completed = await db.execute(
                select(func.count(UserCourseNodeTaskProgress.id)).where(
                    UserCourseNodeTaskProgress.user_id == user_id,
                    UserCourseNodeTaskProgress.node_task_id.in_(list(node_task_ids)),
                    UserCourseNodeTaskProgress.status == NodeTaskProgressStatus.completed,
                )
            )
            completed_tasks_count = int(r_completed.scalar() or 0)
            progress_percent = (
                float(completed_tasks_count) / float(total_tasks_count) * 100.0
            )

    r_progress = await db.execute(
        select(UserCourseProgress).where(
            UserCourseProgress.user_id == user_id,
            UserCourseProgress.course_id == course_id,
        )
    )
    progress = r_progress.scalar_one_or_none()
    if progress is None:
        progress = UserCourseProgress(
            user_id=user_id,
            course_id=course_id,
            progress_percent=progress_percent,
            completed_tasks_count=completed_tasks_count,
            total_tasks_count=total_tasks_count,
        )
        db.add(progress)
    else:
        progress.progress_percent = progress_percent
        progress.completed_tasks_count = completed_tasks_count
        progress.total_tasks_count = total_tasks_count

    await db.flush()

