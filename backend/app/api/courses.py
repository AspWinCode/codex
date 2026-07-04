from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth_middleware import get_current_user, require_admin
from app.models.course import Course, CourseStatus
from app.models.course_node import CourseNode, CourseNodeStatus
from app.models.module import Module
from app.models.submodule import Submodule
from app.models.user import User
from app.models.user_course_enrollment import UserCourseEnrollment
from app.schemas.course import (
    CourseCreate,
    CourseDetailOut,
    CourseOut,
    CourseUpdate,
    ModuleCreate,
    ModuleDetailOut,
    ModuleOut,
    ModuleUpdate,
    SubmoduleCreate,
    SubmoduleOut,
    SubmoduleUpdate,
)
from app.schemas.course_hierarchy import CourseNodeTreeOut

router = APIRouter()


# --- Courses ---


def _build_node_tree(node: CourseNode) -> CourseNodeTreeOut:
    # Для публичного дерева студентам флаги container/leaf и кол-во задач не считаем пока,
    # эта ответственность лежит на специализированном student API.
    return CourseNodeTreeOut(
        id=node.id,
        course_id=node.course_id,
        parent_id=node.parent_id,
        type=node.type,
        title=node.title,
        sort_order=node.sort_order,
        status=node.status,
        has_children=len(node.children) > 0,
        task_count=len(node.node_tasks),
        can_attach_tasks=False,
        can_create_children=False,
        children=[_build_node_tree(c) for c in sorted(node.children, key=lambda n: n.sort_order)],
    )


@router.get("", response_model=List[CourseOut])
async def list_courses(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(Course).order_by(Course.sort_order, Course.id)
    if user.role == "student":
        q = q.where(Course.status == CourseStatus.published)
        # Студент видит только те курсы, к которым у него есть доступ (enrollment).
        # Если зачислений нет — курсов не показываем.
        enrollment_r = await db.execute(
            select(UserCourseEnrollment.course_id).where(
                UserCourseEnrollment.user_id == user.id
            )
        )
        enrolled_ids = [row[0] for row in enrollment_r.fetchall()]
        q = q.where(Course.id.in_(enrolled_ids))
    result = await db.execute(q)
    return [CourseOut.model_validate(c) for c in result.scalars().all()]


@router.get("/{course_id}/tree", response_model=List[CourseNodeTreeOut])
async def get_course_tree(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    r = await db.execute(select(Course).where(Course.id == course_id))
    course = r.scalar_one_or_none()
    if not course or (user.role == "student" and course.status != CourseStatus.published):
        raise HTTPException(status_code=404, detail="Course not found")
    r2 = await db.execute(
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
        )
        .order_by(CourseNode.sort_order, CourseNode.id)
    )
    roots = r2.scalars().unique().all()
    if user.role == "student":
        # Студент видит только опубликованные ветки: статус published у курса и всех узлов по пути.
        roots = [n for n in roots if n.status == CourseNodeStatus.published]
    return [_build_node_tree(n) for n in roots]


@router.get("/{course_id}", response_model=CourseDetailOut)
async def get_course(course_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(
        select(Course)
        .options(selectinload(Course.modules).selectinload(Module.submodules))
        .where(Course.id == course_id)
    )
    course = result.scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return CourseDetailOut.model_validate(course)


@router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
async def create_course(body: CourseCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    course = Course(**body.model_dump())
    db.add(course)
    await db.flush()
    await db.refresh(course)
    return CourseOut.model_validate(course)


@router.put("/{course_id}", response_model=CourseOut)
async def update_course(course_id: int, body: CourseUpdate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(course, field, value)
    await db.flush()
    await db.refresh(course)
    return CourseOut.model_validate(course)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(course_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    await db.delete(course)


# --- Modules ---

@router.get("/{course_id}/modules", response_model=List[ModuleDetailOut])
async def list_modules(course_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(
        select(Module)
        .options(selectinload(Module.submodules))
        .where(Module.course_id == course_id)
        .order_by(Module.order_index)
    )
    return [ModuleDetailOut.model_validate(m) for m in result.scalars().all()]


@router.post("/{course_id}/modules", response_model=ModuleOut, status_code=status.HTTP_201_CREATED)
async def create_module(course_id: int, body: ModuleCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    module = Module(course_id=course_id, title=body.title, order_index=body.order_index)
    db.add(module)
    await db.flush()
    await db.refresh(module)
    return ModuleOut.model_validate(module)


@router.put("/modules/{module_id}", response_model=ModuleOut)
async def update_module(module_id: int, body: ModuleUpdate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(Module).where(Module.id == module_id))
    module = result.scalar_one_or_none()
    if module is None:
        raise HTTPException(status_code=404, detail="Module not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(module, field, value)
    await db.flush()
    await db.refresh(module)
    return ModuleOut.model_validate(module)


@router.delete("/modules/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_module(module_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(Module).where(Module.id == module_id))
    module = result.scalar_one_or_none()
    if module is None:
        raise HTTPException(status_code=404, detail="Module not found")
    await db.delete(module)


# --- Submodules ---

@router.post("/modules/{module_id}/submodules", response_model=SubmoduleOut, status_code=status.HTTP_201_CREATED)
async def create_submodule(module_id: int, body: SubmoduleCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    submodule = Submodule(module_id=module_id, title=body.title, order_index=body.order_index)
    db.add(submodule)
    await db.flush()
    await db.refresh(submodule)
    return SubmoduleOut.model_validate(submodule)


@router.put("/submodules/{submodule_id}", response_model=SubmoduleOut)
async def update_submodule(submodule_id: int, body: SubmoduleUpdate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(Submodule).where(Submodule.id == submodule_id))
    submodule = result.scalar_one_or_none()
    if submodule is None:
        raise HTTPException(status_code=404, detail="Submodule not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(submodule, field, value)
    await db.flush()
    await db.refresh(submodule)
    return SubmoduleOut.model_validate(submodule)


@router.delete("/submodules/{submodule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_submodule(submodule_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.execute(select(Submodule).where(Submodule.id == submodule_id))
    submodule = result.scalar_one_or_none()
    if submodule is None:
        raise HTTPException(status_code=404, detail="Submodule not found")
    await db.delete(submodule)
