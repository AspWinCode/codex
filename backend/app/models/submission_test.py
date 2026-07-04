from typing import Optional

from sqlalchemy import Enum, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.submission import Verdict


class SubmissionTest(Base):
    __tablename__ = "submission_tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"))
    test_id: Mapped[int] = mapped_column(ForeignKey("task_tests.id", ondelete="CASCADE"))
    verdict: Mapped[Optional[Verdict]] = mapped_column(Enum(Verdict), nullable=True)
    runtime: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    submission = relationship("Submission", back_populates="test_results")
    test = relationship("TaskTest", back_populates="submission_tests")
