"""Schemas for course hierarchy: Course, CourseNode, node tasks, progress."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.course import CourseStatus
from app.models.course_node import CourseNodeStatus, CourseNodeType


# --- Course (admin) ---


class CourseAdminCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    slug: Optional[str] = Field(default=None, max_length=255, pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
    description: Optional[str] = None
    short_description: Optional[str] = None
    cover_image_url: Optional[str] = None
    status: CourseStatus = CourseStatus.draft
    sort_order: int = 0


class CourseAdminUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    slug: Optional[str] = Field(default=None, max_length=255, pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
    description: Optional[str] = None
    short_description: Optional[str] = None
    cover_image_url: Optional[str] = None
    status: Optional[CourseStatus] = None
    sort_order: Optional[int] = None


class CourseAdminOut(BaseModel):
    id: int
    title: str
    slug: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    cover_image_url: Optional[str] = None
    status: CourseStatus
    sort_order: int
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# --- CourseNode ---

class CourseNodeOut(BaseModel):
    id: int
    course_id: int
    parent_id: Optional[int] = None
    type: CourseNodeType
    title: str
    description: Optional[str] = None
    sort_order: int
    status: CourseNodeStatus
    has_children: bool
    task_count: int
    can_attach_tasks: bool
    can_create_children: bool
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None
    children: List["CourseNodeTreeOut"] = []

    model_config = {"from_attributes": True}


class CourseNodeTreeOut(BaseModel):
    id: int
    course_id: int
    parent_id: Optional[int] = None
    type: CourseNodeType
    title: str
    sort_order: int
    status: CourseNodeStatus
    has_children: bool
    task_count: int
    can_attach_tasks: bool
    can_create_children: bool
    children: List["CourseNodeTreeOut"] = []

    model_config = {"from_attributes": True}


# Fix forward ref
CourseNodeOut.model_rebuild()
CourseNodeTreeOut.model_rebuild()


class CourseNodeCreate(BaseModel):
    parent_id: Optional[int] = None
    type: CourseNodeType
    title: str
    description: Optional[str] = None
    sort_order: int = 0
    status: CourseNodeStatus = CourseNodeStatus.draft


class CourseNodeUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    status: Optional[CourseNodeStatus] = None
    # status only; allowed transitions и бизнес-валидация делаются на сервисе


# --- Course node tasks ---


class CourseNodeTaskCreate(BaseModel):
    # Вариант 1: привязать существующую задачу
    task_id: Optional[int] = None
    # Вариант 2: создать новую задачу и привязать
    create_new_task: bool = False
    task_title: Optional[str] = None
    sort_order: Optional[int] = None
    is_required: bool = True


class CourseNodeTaskOut(BaseModel):
    id: int
    node_id: int
    task_id: int
    task_title: str
    sort_order: int
    is_required: bool

    model_config = {"from_attributes": True}


class CourseNodeTaskReorderItem(BaseModel):
    id: int
    sort_order: int


# --- Node move / reorder ---

class CourseNodeMovePayload(BaseModel):
    """Тело запроса для перемещения узла дерева."""
    new_parent_id: Optional[int] = None
    new_sort_order: Optional[int] = None


class CourseNodeReorderItem(BaseModel):
    """Элемент списка для переупорядочивания соседних узлов."""
    id: int
    sort_order: int


# --- Course node content (lecture/theory) ---


class CourseNodeContentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str
    sort_order: int = 0


class CourseNodeContentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    content: Optional[str] = None
    sort_order: Optional[int] = None


class CourseNodeContentOut(BaseModel):
    id: int
    node_id: int
    title: str
    content: str
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Progress ---


class UserCourseProgressOut(BaseModel):
    course_id: int
    progress_percent: float
    completed_tasks_count: int
    total_tasks_count: int
    current_node_id: Optional[int] = None
    last_task_id: Optional[int] = None

    model_config = {"from_attributes": True}


class UserNodeTaskProgressOut(BaseModel):
    node_task_id: int
    task_id: int
    task_title: str = ""
    status: str
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
