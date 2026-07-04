import enum
from datetime import datetime

from typing import Optional

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SubmissionStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    finished = "finished"


class Verdict(str, enum.Enum):
    AC = "AC"   # Accepted
    WA = "WA"   # Wrong Answer
    RE = "RE"   # Runtime Error
    TLE = "TLE" # Time Limit Exceeded
    MLE = "MLE" # Memory Limit Exceeded
    CE = "CE"   # Compilation Error
    PE = "PE"   # Presentation Error
    IE = "IE"   # Internal Error


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(Text)
    status: Mapped[SubmissionStatus] = mapped_column(Enum(SubmissionStatus), default=SubmissionStatus.queued)
    verdict: Mapped[Optional[Verdict]] = mapped_column(Enum(Verdict), nullable=True)
    runtime: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    memory: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    task = relationship("Task", back_populates="submissions")
    user = relationship("User", back_populates="submissions")
    test_results = relationship("SubmissionTest", back_populates="submission", cascade="all, delete-orphan")
