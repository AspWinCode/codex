from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.models.course import CourseStatus


class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: CourseStatus = CourseStatus.draft


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CourseStatus] = None


class ModuleCreate(BaseModel):
    course_id: int
    title: str
    order_index: int = 0


class ModuleUpdate(BaseModel):
    title: Optional[str] = None
    order_index: Optional[int] = None


class ModuleOut(BaseModel):
    id: int
    course_id: int
    title: str
    order_index: int

    model_config = {"from_attributes": True}


class SubmoduleCreate(BaseModel):
    module_id: int
    title: str
    order_index: int = 0


class SubmoduleUpdate(BaseModel):
    title: Optional[str] = None
    order_index: Optional[int] = None


class SubmoduleOut(BaseModel):
    id: int
    module_id: int
    title: str
    order_index: int

    model_config = {"from_attributes": True}


class CourseOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: CourseStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class CourseDetailOut(CourseOut):
    modules: List[ModuleOut] = []


class ModuleDetailOut(ModuleOut):
    submodules: List[SubmoduleOut] = []
