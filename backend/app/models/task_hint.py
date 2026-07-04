from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TaskHint(Base):
    __tablename__ = "task_hints"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    hint_level: Mapped[int] = mapped_column(Integer, default=1)
    unlock_attempts: Mapped[int] = mapped_column(Integer, default=3)
    coin_cost: Mapped[int] = mapped_column(Integer, default=30)
    content: Mapped[str] = mapped_column(Text)

    task = relationship("Task", back_populates="hints")
