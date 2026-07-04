"""Student API: course tree, progress and node-task progress."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.course import Course, CourseStatus
from app.models.course_node import CourseNode, CourseNodeStatus
from app.models.course_node_content import CourseNodeContent
from app.models.course_node_task import CourseNodeTask
from app.models.user import User
from app.models.user_course_node_task_progress import UserCourseNodeTaskProgress
from app.models.user_course_progress import UserCourseProgress
from app.schemas.course_hierarchy import (
    CourseNodeContentOut,
    CourseNodeTreeOut,
    UserCourseProgressOut,
    UserNodeTaskProgressOut,
)
from app.services.course_progress_service import recalculate_course_progress

router = APIRouter(dependencies=[Depends(get_current_user)])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_student_node_tree(node: CourseNode) -> CourseNodeTreeOut:
    """Рекурсивно строит дерево, включая только опубликованные дочерние узлы."""
    published_children = [
        c for c in sorted(node.children, key=lambda n: n.sort_order)
        if c.status == CourseNodeStatus.published
    ]
    task_count = len(node.node_tasks)
    has_children = len(published_children) > 0
    return CourseNodeTreeOut(
        id=node.id,
        course_id=node.course_id,
        parent_id=node.parent_id,
        type=node.type,
        title=node.title,
        sort_order=node.sort_order,
        status=node.status,
        has_children=has_children,
        task_count=task_count,
        can_attach_tasks=False,       # студентам не нужно
        can_create_children=False,    # студентам не нужно
        children=[_build_student_node_tree(c) for c in published_children],
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/courses/{course_id}/tree", response_model=List[CourseNodeTreeOut])
async def student_get_course_tree(
    course_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Дерево узлов курса (только опубликованные) для студента."""
    r_course = await db.execute(select(Course).where(Course.id == course_id))
    course = r_course.scalar_one_or_none()
    if not course or course.status != CourseStatus.published:
        raise HTTPException(status_code=404, detail="Course not found")

    r = await db.execute(
        select(CourseNode)
        .options(
            selectinload(CourseNode.node_tasks),
            selectinload(CourseNode.children).options(
                selectinload(CourseNode.node_tasks),
                selectinload(CourseNode.children).options(
                    selectinload(CourseNode.node_tasks),
                    selectinload(CourseNode.children).selectinload(CourseNode.node_tasks),
                ),
            ),
        )
        .where(
            CourseNode.course_id == course_id,
            CourseNode.parent_id.is_(None),
            CourseNode.status == CourseNodeStatus.published,
        )
        .order_by(CourseNode.sort_order, CourseNode.id)
    )
    roots = r.scalars().unique().all()
    return [_build_student_node_tree(n) for n in roots]


@router.get("/courses/{course_id}/progress", response_model=UserCourseProgressOut)
async def student_get_course_progress(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Общий прогресс пользователя по курсу."""
    r_course = await db.execute(select(Course).where(Course.id == course_id))
    course = r_course.scalar_one_or_none()
    if not course or course.status != CourseStatus.published:
        raise HTTPException(status_code=404, detail="Course not found")

    # Всегда пересчитываем прогресс (задачи могли быть добавлены/удалены)
    await recalculate_course_progress(db, user_id=user.id, course_id=course_id)
    r = await db.execute(
        select(UserCourseProgress).where(
            UserCourseProgress.user_id == user.id,
            UserCourseProgress.course_id == course_id,
        )
    )
    p = r.scalar_one_or_none()
    if not p:
        return UserCourseProgressOut(
            course_id=course_id,
            progress_percent=0.0,
            completed_tasks_count=0,
            total_tasks_count=0,
        )
    return UserCourseProgressOut.model_validate(p)


@router.get("/nodes/{node_id}/tasks", response_model=List[UserNodeTaskProgressOut])
async def student_get_node_tasks_with_progress(
    node_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Список задач узла с прогрессом пользователя."""
    r_node = await db.execute(
        select(CourseNode)
        .options(selectinload(CourseNode.children))
        .where(CourseNode.id == node_id)
    )
    node = r_node.scalar_one_or_none()
    if not node or node.status != CourseNodeStatus.published:
        raise HTTPException(status_code=404, detail="Node not found")

    r_tasks = await db.execute(
        select(CourseNodeTask)
        .options(selectinload(CourseNodeTask.task))
        .where(CourseNodeTask.node_id == node_id)
        .order_by(CourseNodeTask.sort_order, CourseNodeTask.id)
    )
    node_tasks = r_tasks.scalars().all()

    if not node_tasks:
        return []

    task_ids = [nt.id for nt in node_tasks]
    r_progress = await db.execute(
        select(UserCourseNodeTaskProgress).where(
            UserCourseNodeTaskProgress.user_id == user.id,
            UserCourseNodeTaskProgress.node_task_id.in_(task_ids),
        )
    )
    progress_by_node_task = {
        p.node_task_id: p for p in r_progress.scalars().all()
    }

    result: List[UserNodeTaskProgressOut] = []
    for nt in node_tasks:
        p = progress_by_node_task.get(nt.id)
        result.append(
            UserNodeTaskProgressOut(
                node_task_id=nt.id,
                task_id=nt.task_id,
                task_title=nt.task.title if nt.task else f"Задача #{nt.task_id}",
                status=p.status.value if p else "not_started",
                completed_at=p.completed_at if p else None,
            )
        )
    return result


@router.get("/nodes/{node_id}/content", response_model=List[CourseNodeContentOut])
async def student_get_node_content(
    node_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Лекционные материалы узла для студента."""
    r_node = await db.execute(select(CourseNode).where(CourseNode.id == node_id))
    node = r_node.scalar_one_or_none()
    if not node or node.status != CourseNodeStatus.published:
        raise HTTPException(status_code=404, detail="Node not found")

    r = await db.execute(
        select(CourseNodeContent)
        .where(CourseNodeContent.node_id == node_id)
        .order_by(CourseNodeContent.sort_order, CourseNodeContent.id)
    )
    return [CourseNodeContentOut.model_validate(item) for item in r.scalars().all()]
