from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class StudentProgress(Base):
    __tablename__ = "student_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    best_verdict: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    solved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_submission_id: Mapped[Optional[int]] = mapped_column(ForeignKey("submissions.id", ondelete="SET NULL"), nullable=True)

    user = relationship("User", back_populates="progress")
    task = relationship("Task", back_populates="progress")
