from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TaskLecture(Base):
    __tablename__ = "task_lectures"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text)
    unlock_attempts: Mapped[int] = mapped_column(Integer, default=0)

    task = relationship("Task", back_populates="lectures")
