from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class NodeTaskProgressStatus(str, enum.Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"


class UserCourseNodeTaskProgress(Base):
    __tablename__ = "user_course_node_task_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    node_task_id: Mapped[int] = mapped_column(ForeignKey("course_node_tasks.id", ondelete="CASCADE"))
    status: Mapped[NodeTaskProgressStatus] = mapped_column(
        Enum(NodeTaskProgressStatus, name="node_task_progress_status", create_type=False),
        default=NodeTaskProgressStatus.not_started,
    )
    best_submission_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("submissions.id", ondelete="SET NULL"),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship("User", back_populates="node_task_progress")
    node_task = relationship("CourseNodeTask")
    best_submission = relationship("Submission")

