"""Универсальный узел дерева курса: модуль, подмодуль, тема, подтема."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CourseNodeType(str, enum.Enum):
    module = "module"
    submodule = "submodule"
    topic = "topic"
    subtopic = "subtopic"


class CourseNodeStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class CourseNode(Base):
    __tablename__ = "course_nodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("course_nodes.id", ondelete="CASCADE"),
        nullable=True,
    )
    type: Mapped[CourseNodeType] = mapped_column(
        Enum(CourseNodeType, name="coursenodetype", create_type=False)
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[CourseNodeStatus] = mapped_column(
        Enum(CourseNodeStatus, name="coursestatus", create_type=False),
        default=CourseNodeStatus.draft,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    course = relationship("Course", back_populates="nodes", foreign_keys=[course_id])
    parent = relationship(
        "CourseNode",
        remote_side="CourseNode.id",
        back_populates="children",
        foreign_keys=[parent_id],
    )
    children = relationship(
        "CourseNode",
        back_populates="parent",
        cascade="all, delete-orphan",
        foreign_keys=[parent_id],
        order_by="CourseNode.sort_order",
    )

    node_tasks = relationship(
        "CourseNodeTask",
        back_populates="node",
        cascade="all, delete-orphan",
        order_by="CourseNodeTask.sort_order",
    )

    content_items = relationship(
        "CourseNodeContent",
        back_populates="node",
        cascade="all, delete-orphan",
        order_by="CourseNodeContent.sort_order",
    )
