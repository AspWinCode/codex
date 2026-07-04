import enum

from typing import Any, List, Optional

from sqlalchemy import JSON, Enum, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TestType(str, enum.Enum):
    public = "public"
    hidden = "hidden"


class TaskTest(Base):
    __tablename__ = "task_tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    test_type: Mapped[TestType] = mapped_column(Enum(TestType), default=TestType.public)
    input_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verification_sql: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # List of {"name": str, "content": str} — extra files written to sandbox workspace
    test_files: Mapped[Optional[List[Any]]] = mapped_column(JSON, nullable=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    task = relationship("Task", back_populates="tests")
    submission_tests = relationship("SubmissionTest", back_populates="test", passive_deletes=True)
