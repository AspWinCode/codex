"""Прогресс пользователя по курсу (новая модель, только задачи)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserCourseProgress(Base):
    __tablename__ = "user_course_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0)
    completed_tasks_count: Mapped[int] = mapped_column(Integer, default=0)
    total_tasks_count: Mapped[int] = mapped_column(Integer, default=0)
    current_node_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("course_nodes.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_task_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship("User", back_populates="course_progress")
    course = relationship("Course", back_populates="user_progress")
