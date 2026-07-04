"""Admin API: courses, course tree (CourseNode), tasks on nodes."""
from __future__ import annotations

from typing import List

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth_middleware import require_admin
from app.models.course import Course, CourseStatus
from app.models.course_node import CourseNode, CourseNodeStatus, CourseNodeType
from app.models.course_node_content import CourseNodeContent
from app.models.course_node_task import CourseNodeTask
from app.models.task import Task, TaskStatus, TaskType, RunnerType
from app.models.user_course_progress import UserCourseProgress
from app.schemas.course_hierarchy import (
    CourseAdminCreate,
    CourseAdminOut,
    CourseAdminUpdate,
    CourseNodeCreate,
    CourseNodeContentCreate,
    CourseNodeContentOut,
    CourseNodeContentUpdate,
    CourseNodeMovePayload,
    CourseNodeOut,
    CourseNodeReorderItem,
    CourseNodeTreeOut,
    CourseNodeUpdate,
    CourseNodeTaskCreate,
    CourseNodeTaskOut,
    CourseNodeTaskReorderItem,
)
from app.services.course_node_service import (
    can_attach_task,
    can_create_child,
    get_node,
    is_leaf_node,
    validate_move,
)
from app.services.course_progress_service import recalculate_course_progress
from app.schemas.task import TaskCreate, TaskOut

router = APIRouter(prefix="/admin/courses", dependencies=[Depends(require_admin)])


async def _get_course_task_ids(db: AsyncSession, course_id: int) -> list[int]:
    """Получить все task_id, привязанные к курсу через узлы."""
    r = await db.execute(
        select(CourseNodeTask.task_id)
        .join(CourseNode)
        .where(CourseNode.course_id == course_id)
        .distinct()
    )
    return [row[0] for row in r.fetchall()]


def _compute_node_flags(node: CourseNode) -> dict:
    """Вычислить служебные флаги для узла."""
    has_children = len(node.children) > 0
    task_count = len(node.node_tasks)
    can_attach_tasks = can_attach_task(node)
    can_create_children = can_create_child(node)
    return {
        "has_children": has_children,
        "task_count": task_count,
        "can_attach_tasks": can_attach_tasks,
        "can_create_children": can_create_children,
    }


def _build_node_tree(node: CourseNode) -> CourseNodeTreeOut:
    flags = _compute_node_flags(node)
    return CourseNodeTreeOut(
        id=node.id,
        course_id=node.course_id,
        parent_id=node.parent_id,
        type=node.type,
        title=node.title,
        sort_order=node.sort_order,
        status=node.status,
        has_children=flags["has_children"],
        task_count=flags["task_count"],
        can_attach_tasks=flags["can_attach_tasks"],
        can_create_children=flags["can_create_children"],
        children=[_build_node_tree(c) for c in sorted(node.children, key=lambda n: n.sort_order)],
    )


# --- Admin: Courses ---

@router.get("", response_model=List[CourseAdminOut])
async def admin_list_courses(db: AsyncSession = Depends(get_db)):
    try:
        r = await db.execute(select(Course).order_by(Course.sort_order, Course.id))
        return [CourseAdminOut.model_validate(c) for c in r.scalars().all()]
    except Exception:
        return []


@router.post("", response_model=CourseAdminOut, status_code=status.HTTP_201_CREATED)
async def admin_create_course(body: CourseAdminCreate, db: AsyncSession = Depends(get_db)):
    # Проверка уникальности slug при создании
    if body.slug:
        r_slug = await db.execute(select(Course).where(Course.slug == body.slug))
        if r_slug.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Course with this slug already exists")
    course = Course(
        title=body.title,
        slug=body.slug,
        description=body.description,
        short_description=body.short_description,
        cover_image_url=body.cover_image_url,
        status=body.status or CourseStatus.draft,
        sort_order=body.sort_order,
    )
    db.add(course)
    await db.flush()
    await db.refresh(course)
    return CourseAdminOut.model_validate(course)


@router.get("/{course_id}", response_model=CourseAdminOut)
async def admin_get_course(course_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Course).where(Course.id == course_id))
    course = r.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return CourseAdminOut.model_validate(course)


@router.patch("/{course_id}", response_model=CourseAdminOut)
async def admin_update_course(course_id: int, body: CourseAdminUpdate, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Course).where(Course.id == course_id))
    course = r.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    updates = body.model_dump(exclude_unset=True)

    # Проверка уникальности slug, если он меняется
    if "slug" in updates and updates["slug"] and updates["slug"] != course.slug:
        r_slug = await db.execute(
            select(Course).where(Course.slug == updates["slug"], Course.id != course_id)
        )
        if r_slug.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Course with this slug already exists")

    for k, v in updates.items():
        setattr(course, k, v)
    if "status" in updates:
        if updates["status"] == CourseStatus.archived:
            course.archived_at = datetime.now(timezone.utc)
        else:
            course.archived_at = None
    await db.flush()
    await db.refresh(course)
    return CourseAdminOut.model_validate(course)


@router.post("/{course_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
async def admin_archive_course(course_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Course).where(Course.id == course_id))
    course = r.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    course.status = CourseStatus.archived
    course.archived_at = datetime.now(timezone.utc)
    # Скрываем все задачи этого курса (archived)
    task_ids = await _get_course_task_ids(db, course_id)
    if task_ids:
        await db.execute(
            update(Task)
            .where(Task.id.in_(task_ids))
            .values(status=TaskStatus.archived)
        )
    await db.flush()
    return None


@router.post("/{course_id}/unarchive", status_code=status.HTTP_204_NO_CONTENT)
async def admin_unarchive_course(course_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Course).where(Course.id == course_id))
    course = r.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    # Разархивирование → published, возвращаем задачи тоже
    course.status = CourseStatus.published
    course.archived_at = None
    task_ids = await _get_course_task_ids(db, course_id)
    if task_ids:
        await db.execute(
            update(Task)
            .where(Task.id.in_(task_ids), Task.status == TaskStatus.archived)
            .values(status=TaskStatus.published)
        )
    await db.flush()
    return None


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_course(course_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Course).where(Course.id == course_id))
    course = r.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    # Удаляем задачи, которые принадлежат ТОЛЬКО этому курсу
    task_ids = await _get_course_task_ids(db, course_id)
    if task_ids:
        # Находим задачи, которые НЕ используются в других курсах
        for tid in task_ids:
            r_other = await db.execute(
                select(CourseNodeTask.id).join(CourseNode).where(
                    CourseNodeTask.task_id == tid,
                    CourseNode.course_id != course_id,
                )
            )
            if not r_other.first():
                # Задача только в этом курсе — удаляем
                r_task = await db.execute(select(Task).where(Task.id == tid))
                task_obj = r_task.scalar_one_or_none()
                if task_obj:
                    await db.delete(task_obj)
    await db.delete(course)
    return None


# --- Admin: Tree ---

@router.get("/{course_id}/tree", response_model=List[CourseNodeTreeOut])
async def admin_get_tree(course_id: int, db: AsyncSession = Depends(get_db)):
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
            .where(CourseNode.course_id == course_id, CourseNode.parent_id.is_(None))
            .order_by(CourseNode.sort_order, CourseNode.id)
    )
    roots = r.scalars().unique().all()
    return [_build_node_tree(n) for n in roots]


@router.post("/{course_id}/nodes", response_model=CourseNodeOut, status_code=status.HTTP_201_CREATED)
async def admin_create_node(course_id: int, body: CourseNodeCreate, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Course).where(Course.id == course_id))
    course = r.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.status == CourseStatus.archived:
        raise HTTPException(status_code=400, detail="Cannot add node to archived course")
    if body.parent_id is not None:
        parent = await get_node(db, body.parent_id)
        if not parent or parent.course_id != course_id:
            raise HTTPException(status_code=400, detail="Parent node not found in this course")
        if not can_create_child(parent):
            raise HTTPException(status_code=400, detail="Cannot add child to this node")
    node = CourseNode(
        course_id=course_id,
        parent_id=body.parent_id,
        type=body.type,
        title=body.title,
        description=body.description,
        sort_order=body.sort_order,
        status=body.status,
    )
    db.add(node)
    await db.flush()
    # Перезагружаем узел с relationships чтобы _compute_node_flags не делал lazy-load
    node = await get_node(db, node.id)
    flags = _compute_node_flags(node)
    return CourseNodeOut(
        id=node.id,
        course_id=node.course_id,
        parent_id=node.parent_id,
        type=node.type,
        title=node.title,
        description=node.description,
        sort_order=node.sort_order,
        status=node.status,
        has_children=flags["has_children"],
        task_count=flags["task_count"],
        can_attach_tasks=flags["can_attach_tasks"],
        can_create_children=flags["can_create_children"],
        created_at=node.created_at,
        updated_at=node.updated_at,
        archived_at=node.archived_at,
        children=[],
    )


# --- Admin: Node by id (global) ---

@router.get("/nodes/{node_id}", response_model=CourseNodeOut)
async def admin_get_node(node_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        select(CourseNode)
        .options(
            selectinload(CourseNode.node_tasks).selectinload(CourseNodeTask.task),
            selectinload(CourseNode.children).options(
                selectinload(CourseNode.node_tasks),
                selectinload(CourseNode.children).options(
                    selectinload(CourseNode.node_tasks),
                    selectinload(CourseNode.children).selectinload(CourseNode.node_tasks),
                ),
            ),
        )
        .where(CourseNode.id == node_id)
    )
    node = r.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    flags = _compute_node_flags(node)
    return CourseNodeOut(
        id=node.id,
        course_id=node.course_id,
        parent_id=node.parent_id,
        type=node.type,
        title=node.title,
        description=node.description,
        sort_order=node.sort_order,
        status=node.status,
        has_children=flags["has_children"],
        task_count=flags["task_count"],
        can_attach_tasks=flags["can_attach_tasks"],
        can_create_children=flags["can_create_children"],
        created_at=node.created_at,
        updated_at=node.updated_at,
        archived_at=node.archived_at,
        children=[
            _build_node_tree(child)
            for child in sorted(node.children, key=lambda c: c.sort_order)
        ],
    )


@router.patch("/nodes/{node_id}", response_model=CourseNodeOut)
async def admin_update_node(node_id: int, body: CourseNodeUpdate, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(CourseNode).where(CourseNode.id == node_id))
    node = r.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    updates = body.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(node, k, v)
    if "status" in updates:
        if updates["status"] == CourseNodeStatus.archived:
            node.archived_at = datetime.now(timezone.utc)
        else:
            node.archived_at = None
    await db.flush()
    node = await get_node(db, node_id)
    flags = _compute_node_flags(node)
    return CourseNodeOut(
        id=node.id,
        course_id=node.course_id,
        parent_id=node.parent_id,
        type=node.type,
        title=node.title,
        description=node.description,
        sort_order=node.sort_order,
        status=node.status,
        has_children=flags["has_children"],
        task_count=flags["task_count"],
        can_attach_tasks=flags["can_attach_tasks"],
        can_create_children=flags["can_create_children"],
        created_at=node.created_at,
        updated_at=node.updated_at,
        archived_at=node.archived_at,
        children=[],
    )


@router.post("/nodes/{node_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
async def admin_archive_node(node_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(CourseNode).where(CourseNode.id == node_id))
    node = r.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    node.status = CourseNodeStatus.archived
    node.archived_at = datetime.now(timezone.utc)
    await db.flush()
    return None


@router.post("/nodes/{node_id}/unarchive", status_code=status.HTTP_204_NO_CONTENT)
async def admin_unarchive_node(node_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(CourseNode).where(CourseNode.id == node_id))
    node = r.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    # Разархивирование → published (а не draft): узел сразу виден студентам
    node.status = CourseNodeStatus.published
    node.archived_at = None
    await db.flush()
    return None


@router.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_node(node_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(CourseNode).where(CourseNode.id == node_id))
    node = r.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    course_id = node.course_id

    # Собираем затронутых пользователей ДО удаления, пока прогресс ещё существует.
    # Берём всех пользователей у которых есть прогресс по данному курсу —
    # после удаления узла их счётчики должны быть пересчитаны.
    r_users = await db.execute(
        select(UserCourseProgress.user_id).where(UserCourseProgress.course_id == course_id)
    )
    affected_user_ids = [row[0] for row in r_users.fetchall()]

    await db.delete(node)
    await db.flush()  # каскадное удаление node_tasks и прогресса происходит здесь

    # Пересчитываем прогресс для всех затронутых пользователей
    for user_id in affected_user_ids:
        await recalculate_course_progress(db, user_id=user_id, course_id=course_id)

    return None


# --- Admin: Node tasks ---


@router.get("/nodes/{node_id}/tasks", response_model=List[CourseNodeTaskOut])
async def admin_get_node_tasks(node_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        select(CourseNodeTask)
        .options(selectinload(CourseNodeTask.task))
        .where(CourseNodeTask.node_id == node_id)
        .order_by(CourseNodeTask.sort_order, CourseNodeTask.id)
    )
    rows = r.scalars().all()
    return [
        CourseNodeTaskOut(
            id=row.id,
            node_id=row.node_id,
            task_id=row.task_id,
            task_title=row.task.title,
            sort_order=row.sort_order,
            is_required=row.is_required,
        )
        for row in rows
    ]


@router.post("/nodes/{node_id}/tasks", response_model=CourseNodeTaskOut, status_code=status.HTTP_201_CREATED)
async def admin_attach_task_to_node(
    node_id: int,
    body: CourseNodeTaskCreate,
    db: AsyncSession = Depends(get_db),
):
    node = await get_node(db, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if not can_attach_task(node):
        raise HTTPException(status_code=400, detail="Cannot attach task to this node")

    # Определяем задачу: существующая или новая
    task: Task
    if body.create_new_task:
        if not body.task_title:
            raise HTTPException(status_code=400, detail="task_title is required when create_new_task is true")
        task = Task(
            title=body.task_title,
            description=None,
            task_type=TaskType.python_io,
            runner_type=RunnerType.stdin_runner,
            status=TaskStatus.published,
        )
        db.add(task)
        await db.flush()
    else:
        if not body.task_id:
            raise HTTPException(status_code=400, detail="task_id is required when create_new_task is false")
        r_task = await db.execute(select(Task).where(Task.id == body.task_id))
        task = r_task.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

    # Проверяем уникальность node_id + task_id (защита от двойного прикрепления)
    existing = await db.execute(
        select(CourseNodeTask).where(
            CourseNodeTask.node_id == node_id,
            CourseNodeTask.task_id == task.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Task already attached to this node")

    if body.sort_order is not None:
        sort_order = body.sort_order
    else:
        r_max = await db.execute(
            select(func.max(CourseNodeTask.sort_order)).where(CourseNodeTask.node_id == node_id)
        )
        max_order = r_max.scalar()
        # Явная проверка на None, т.к. (0 or -1) == -1 в Python (0 — falsy)
        sort_order = (max_order if max_order is not None else -1) + 1

    node_task = CourseNodeTask(
        node_id=node_id,
        task_id=task.id,
        sort_order=sort_order,
        is_required=body.is_required,
    )
    db.add(node_task)
    try:
        await db.flush()
    except IntegrityError:
        # Race condition: параллельный запрос успел вставить раньше нас
        await db.rollback()
        raise HTTPException(status_code=400, detail="Task already attached to this node")

    await db.refresh(node_task)
    return CourseNodeTaskOut(
        id=node_task.id,
        node_id=node_task.node_id,
        task_id=node_task.task_id,
        task_title=task.title,
        sort_order=node_task.sort_order,
        is_required=node_task.is_required,
    )


@router.delete("/nodes/{node_id}/tasks/{node_task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_detach_task_from_node(
    node_id: int,
    node_task_id: int,
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(
        select(CourseNodeTask)
        .options(selectinload(CourseNodeTask.node))
        .where(
            CourseNodeTask.id == node_task_id,
            CourseNodeTask.node_id == node_id,
        )
    )
    row = r.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Node task not found")

    course_id = row.node.course_id

    # Собираем затронутых пользователей ДО удаления
    r_users = await db.execute(
        select(UserCourseProgress.user_id).where(UserCourseProgress.course_id == course_id)
    )
    affected_user_ids = [uid for (uid,) in r_users.fetchall()]

    await db.delete(row)
    await db.flush()  # каскадное удаление UserCourseNodeTaskProgress происходит здесь

    # Пересчитываем прогресс для всех затронутых пользователей
    for user_id in affected_user_ids:
        await recalculate_course_progress(db, user_id=user_id, course_id=course_id)

    return None


@router.post("/nodes/{node_id}/tasks/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def admin_reorder_node_tasks(
    node_id: int,
    body: List[CourseNodeTaskReorderItem],
    db: AsyncSession = Depends(get_db),
):
    # Простая переустановка sort_order для указанных связей
    ids = [item.id for item in body]
    if not ids:
        return None
    r = await db.execute(
        select(CourseNodeTask).where(
            CourseNodeTask.node_id == node_id,
            CourseNodeTask.id.in_(ids),
        )
    )
    tasks_by_id = {row.id: row for row in r.scalars().all()}
    for item in body:
        row = tasks_by_id.get(item.id)
        if row:
            row.sort_order = item.sort_order
    await db.flush()
    return None


@router.post("/nodes/{node_id}/move", status_code=status.HTTP_204_NO_CONTENT)
async def admin_move_node(
    node_id: int,
    payload: CourseNodeMovePayload,
    db: AsyncSession = Depends(get_db),
):
    """Переместить узел: смена parent и sort_order."""
    try:
        node, new_parent = await validate_move(
            db,
            node_id=node_id,
            new_parent_id=payload.new_parent_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    node.parent_id = new_parent.id if new_parent is not None else None
    if payload.new_sort_order is not None:
        node.sort_order = payload.new_sort_order
    await db.flush()
    return None


# --- Admin: Node content (lectures/theory) ---


@router.get("/nodes/{node_id}/content", response_model=List[CourseNodeContentOut])
async def admin_get_node_content(node_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(
        select(CourseNodeContent)
        .where(CourseNodeContent.node_id == node_id)
        .order_by(CourseNodeContent.sort_order, CourseNodeContent.id)
    )
    return [CourseNodeContentOut.model_validate(item) for item in r.scalars().all()]


@router.post("/nodes/{node_id}/content", response_model=CourseNodeContentOut, status_code=status.HTTP_201_CREATED)
async def admin_create_node_content(
    node_id: int, body: CourseNodeContentCreate, db: AsyncSession = Depends(get_db)
):
    r = await db.execute(select(CourseNode).where(CourseNode.id == node_id))
    if not r.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Node not found")
    item = CourseNodeContent(
        node_id=node_id,
        title=body.title,
        content=body.content,
        sort_order=body.sort_order,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return CourseNodeContentOut.model_validate(item)


@router.patch("/nodes/{node_id}/content/{content_id}", response_model=CourseNodeContentOut)
async def admin_update_node_content(
    node_id: int, content_id: int, body: CourseNodeContentUpdate, db: AsyncSession = Depends(get_db)
):
    r = await db.execute(
        select(CourseNodeContent).where(
            CourseNodeContent.id == content_id, CourseNodeContent.node_id == node_id
        )
    )
    item = r.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    await db.flush()
    await db.refresh(item)
    return CourseNodeContentOut.model_validate(item)


@router.delete("/nodes/{node_id}/content/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_node_content(
    node_id: int, content_id: int, db: AsyncSession = Depends(get_db)
):
    r = await db.execute(
        select(CourseNodeContent).where(
            CourseNodeContent.id == content_id, CourseNodeContent.node_id == node_id
        )
    )
    item = r.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Content not found")
    await db.delete(item)
    return None


@router.post("/nodes/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def admin_reorder_sibling_nodes(
    items: List[CourseNodeReorderItem],
    db: AsyncSession = Depends(get_db),
):
    """Переупорядочить соседние узлы."""
    if not items:
        return None
    ids = [item.id for item in items]

    r = await db.execute(
        select(CourseNode).where(CourseNode.id.in_(ids))
    )
    nodes_by_id = {n.id: n for n in r.scalars().all()}
    for item in items:
        node = nodes_by_id.get(item.id)
        if node:
            node.sort_order = item.sort_order
    await db.flush()
    return None
