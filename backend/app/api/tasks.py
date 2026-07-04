from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth_middleware import get_current_user, require_admin
from app.models.course import Course, CourseStatus
from app.models.course_node import CourseNode
from app.models.course_node_task import CourseNodeTask
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_hint import TaskHint
from app.models.task_lecture import TaskLecture
from app.models.task_test import TaskTest
from app.models.user import User
from app.models.user_course_enrollment import UserCourseEnrollment
from app.schemas.task import (
    TaskCreate,
    TaskDetailOut,
    TaskHintCreate,
    TaskHintOut,
    TaskLectureCreate,
    TaskLectureOut,
    TaskOut,
    TaskTestCreate,
    TaskTestOut,
    TaskUpdate,
)

router = APIRouter()


class TaskCourseContextOut(BaseModel):
    course_id: int
    course_title: str
    node_title: str


@router.get("", response_model=List[TaskOut])
async def list_tasks(
    submodule_id: Optional[int] = Query(None),
    task_type: Optional[TaskType] = Query(None),
    offset: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    limit = min(limit, 200)
    q = select(Task).order_by(Task.id)
    if submodule_id is not None:
        q = q.where(Task.submodule_id == submodule_id)
    if task_type is not None:
        q = q.where(Task.task_type == task_type)
    # Студенты видят только опубликованные задачи из курсов, к которым у них есть доступ
    if user.role != "admin":
        q = q.where(Task.status == TaskStatus.published)
        # Подзапрос: id задач, привязанных к курсам, в которые зачислен пользователь
        enrolled_task_ids = (
            select(CourseNodeTask.task_id)
            .join(CourseNode, CourseNode.id == CourseNodeTask.node_id)
            .join(UserCourseEnrollment,
                  UserCourseEnrollment.course_id == CourseNode.course_id)
            .where(UserCourseEnrollment.user_id == user.id)
        )
        q = q.where(Task.id.in_(enrolled_task_ids))
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    return [TaskOut.model_validate(t) for t in result.scalars().all()]


@router.get("/{task_id}/context", response_model=List[TaskCourseContextOut])
async def get_task_context(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Возвращает курсы и разделы, в которых находится данная задача."""
    q = (
        select(CourseNodeTask, CourseNode, Course)
        .join(CourseNode, CourseNode.id == CourseNodeTask.node_id)
        .join(Course, Course.id == CourseNode.course_id)
        .where(CourseNodeTask.task_id == task_id)
    )
    if user.role != "admin":
        q = q.where(Course.status == CourseStatus.published)
    result = await db.execute(q)
    rows = result.all()
    return [
        TaskCourseContextOut(
            course_id=row.Course.id,
            course_title=row.Course.title,
            node_title=row.CourseNode.title,
        )
        for row in rows
    ]


@router.get("/{task_id}", response_model=TaskDetailOut)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    from app.services.cache_service import cache_get, cache_set

    # Non-admin: verify published status + course enrollment before serving any data
    if user.role != "admin":
        access_q = (
            select(Task.id)
            .join(CourseNodeTask, CourseNodeTask.task_id == Task.id)
            .join(CourseNode, CourseNode.id == CourseNodeTask.node_id)
            .join(UserCourseEnrollment, UserCourseEnrollment.course_id == CourseNode.course_id)
            .where(
                Task.id == task_id,
                Task.status == TaskStatus.published,
                UserCourseEnrollment.user_id == user.id,
            )
        )
        access = await db.execute(access_q)
        if not access.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Task not found")

    # Fetch task data (full version cached — strip sensitive fields per-request)
    cache_key = "task:{}".format(task_id)
    cached = cache_get(cache_key)
    if cached is not None:
        out = TaskDetailOut.model_validate(cached)
    else:
        result = await db.execute(
            select(Task)
            .options(selectinload(Task.tests), selectinload(Task.hints), selectinload(Task.lectures))
            .where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        out = TaskDetailOut.model_validate(task)
        cache_set(cache_key, out.model_dump(), ttl=300)

    # Strip sensitive test fields for non-admin (expected answers, sql verification, test data files)
    if user.role != "admin":
        for test in out.tests:
            test.expected_output = None
            test.verification_sql = None
            test.test_files = None

        # Подсказки: контент отдаём только если куплена (student_hint_unlocks), иначе прячем
        if out.hints:
            from app.models.gamification import StudentHintUnlock
            hint_ids = [h.id for h in out.hints]
            unlocked_result = await db.execute(
                select(StudentHintUnlock.hint_id).where(
                    StudentHintUnlock.user_id == user.id,
                    StudentHintUnlock.hint_id.in_(hint_ids),
                )
            )
            unlocked_ids = {row[0] for row in unlocked_result.all()}
            for hint in out.hints:
                hint.is_unlocked = hint.id in unlocked_ids
                if not hint.is_unlocked:
                    hint.content = None

    return out


@router.post("", response_model=TaskDetailOut, status_code=status.HTTP_201_CREATED)
async def create_task(body: TaskCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    task = Task(
        submodule_id=body.submodule_id,
        title=body.title,
        description=body.description,
        task_type=body.task_type,
        runner_type=body.runner_type,
        status=body.status,
        reward_coins=body.reward_coins,
        sql_schema=body.sql_schema,
        sql_seed=body.sql_seed,
    )
    db.add(task)
    await db.flush()
    for t in body.tests:
        db.add(TaskTest(task_id=task.id, **t.model_dump()))
    for h in body.hints:
        db.add(TaskHint(task_id=task.id, **h.model_dump()))
    for lec in body.lectures:
        db.add(TaskLecture(task_id=task.id, **lec.model_dump()))
    await db.flush()
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.tests), selectinload(Task.hints), selectinload(Task.lectures))
        .where(Task.id == task.id)
    )
    return TaskDetailOut.model_validate(result.scalar_one())


@router.put("/{task_id}", response_model=TaskOut)
async def update_task(task_id: int, body: TaskUpdate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    from app.services.cache_service import cache_delete
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    task.version += 1
    await db.flush()
    await db.refresh(task)
    cache_delete("task:{}".format(task_id))
    return TaskOut.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    from app.services.cache_service import cache_delete
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)
    cache_delete("task:{}".format(task_id))


# --- Task Tests ---

@router.post("/{task_id}/tests", response_model=TaskTestOut, status_code=status.HTTP_201_CREATED)
async def add_test(task_id: int, body: TaskTestCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    from app.services.cache_service import cache_delete
    test = TaskTest(task_id=task_id, **body.model_dump())
    db.add(test)
    await db.flush()
    await db.refresh(test)
    cache_delete("task:{}".format(task_id))
    return TaskTestOut.model_validate(test)


@router.patch("/tests/{test_id}", response_model=TaskTestOut)
async def update_test(test_id: int, body: TaskTestCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    from app.services.cache_service import cache_delete
    result = await db.execute(select(TaskTest).where(TaskTest.id == test_id))
    test = result.scalar_one_or_none()
    if test is None:
        raise HTTPException(status_code=404, detail="Test not found")
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(test, key, val)
    await db.flush()
    await db.refresh(test)
    cache_delete("task:{}".format(test.task_id))
    return TaskTestOut.model_validate(test)


@router.delete("/tests/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test(test_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    from app.services.cache_service import cache_delete
    result = await db.execute(select(TaskTest).where(TaskTest.id == test_id))
    test = result.scalar_one_or_none()
    if test is None:
        raise HTTPException(status_code=404, detail="Test not found")
    await db.delete(test)
    cache_delete("task:{}".format(test.task_id))


# --- Task Hints ---

@router.post("/{task_id}/hints", response_model=TaskHintOut, status_code=status.HTTP_201_CREATED)
async def add_hint(task_id: int, body: TaskHintCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    from app.services.cache_service import cache_delete
    hint = TaskHint(task_id=task_id, **body.model_dump())
    db.add(hint)
    await db.flush()
    await db.refresh(hint)
    cache_delete("task:{}".format(task_id))
    return TaskHintOut.model_validate(hint)


@router.delete("/hints/{hint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hint(hint_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    from app.services.cache_service import cache_delete
    result = await db.execute(select(TaskHint).where(TaskHint.id == hint_id))
    hint = result.scalar_one_or_none()
    if hint is None:
        raise HTTPException(status_code=404, detail="Hint not found")
    await db.delete(hint)
    cache_delete("task:{}".format(hint.task_id))


@router.post("/hints/{hint_id}/unlock", response_model=TaskHintOut)
async def unlock_hint(hint_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Покупка подсказки за монеты. Куплено один раз — дальше доступно бесплатно."""
    from app.models.gamification import StudentHintUnlock
    from app.services.gamification_service import spend_coins

    result = await db.execute(select(TaskHint).where(TaskHint.id == hint_id))
    hint = result.scalar_one_or_none()
    if hint is None:
        raise HTTPException(status_code=404, detail="Hint not found")

    existing = await db.execute(
        select(StudentHintUnlock).where(
            StudentHintUnlock.user_id == user.id,
            StudentHintUnlock.hint_id == hint_id,
        )
    )
    already_unlocked = existing.scalar_one_or_none()
    if not already_unlocked:
        ok = await spend_coins(db, user.id, hint.coin_cost, reason="hint_unlock", task_id=hint.task_id)
        if not ok:
            raise HTTPException(status_code=402, detail="Недостаточно монет")
        db.add(StudentHintUnlock(user_id=user.id, hint_id=hint_id))
        await db.flush()

    out = TaskHintOut.model_validate(hint)
    out.is_unlocked = True
    return out


# --- Task Lectures ---

@router.post("/{task_id}/lectures", response_model=TaskLectureOut, status_code=status.HTTP_201_CREATED)
async def add_lecture(task_id: int, body: TaskLectureCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    lecture = TaskLecture(task_id=task_id, **body.model_dump())
    db.add(lecture)
    await db.flush()
    await db.refresh(lecture)
    return TaskLectureOut.model_validate(lecture)


@router.delete("/lectures/{lecture_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lecture(lecture_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(TaskLecture).where(TaskLecture.id == lecture_id))
    lecture = result.scalar_one_or_none()
    if lecture is None:
        raise HTTPException(status_code=404, detail="Lecture not found")
    await db.delete(lecture)
