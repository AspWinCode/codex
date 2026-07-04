import enum
from datetime import datetime

from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TaskType(str, enum.Enum):
    python_io = "python_io"
    python_oop = "python_oop"
    python_numpy = "python_numpy"
    sql_query = "sql_query"
    cpp_io = "cpp_io"
    js_io = "js_io"


class RunnerType(str, enum.Enum):
    stdin_runner = "stdin_runner"
    pytest_runner = "pytest_runner"
    sql_runner = "sql_runner"
    cpp_runner = "cpp_runner"
    js_runner = "js_runner"


class TaskStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    submodule_id: Mapped[Optional[int]] = mapped_column(ForeignKey("submodules.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    task_type: Mapped[TaskType] = mapped_column(Enum(TaskType))
    runner_type: Mapped[RunnerType] = mapped_column(Enum(RunnerType))
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.draft)
    version: Mapped[int] = mapped_column(Integer, default=1)
    reward_coins: Mapped[int] = mapped_column(Integer, default=10)
    # SQL-specific fields stored as text
    sql_schema: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sql_seed: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    submodule = relationship("Submodule", back_populates="tasks")
    tests = relationship("TaskTest", back_populates="task", cascade="all, delete-orphan", order_by="TaskTest.order_index")
    hints = relationship("TaskHint", back_populates="task", cascade="all, delete-orphan")
    lectures = relationship("TaskLecture", back_populates="task", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="task", passive_deletes=True)
    progress = relationship("StudentProgress", back_populates="task", passive_deletes=True)
    personal_links = relationship("PersonalLink", back_populates="task", passive_deletes=True)
    course_nodes = relationship(
        "CourseNodeTask",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="CourseNodeTask.sort_order",
    )
