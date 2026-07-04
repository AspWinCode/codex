"""Achievements, contests and ratings tables

Revision ID: 012
Revises: 011
Create Date: 2026-06-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Achievements ──────────────────────────────────────────────────────────
    op.create_table(
        "achievements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("icon", sa.String(50), nullable=False, server_default="star"),
        sa.Column("points", sa.Integer(), nullable=False, server_default="10"),
    )

    op.create_table(
        "user_achievements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("achievement_id", sa.Integer(), sa.ForeignKey("achievements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("earned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_user_achievements_user_id", "user_achievements", ["user_id"])

    # ── Contests ──────────────────────────────────────────────────────────────
    # Тип conteststatus создаётся автоматически как часть DDL create_table ниже
    # (ручной CREATE TYPE + create_type=False на колонке приводит к двойному
    # созданию типа в рамках одной транзакции и падает с "already exists").
    op.create_table(
        "contests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("upcoming", "active", "finished", name="conteststatus"), nullable=False, server_default="upcoming"),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "contest_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("contest_id", sa.Integer(), sa.ForeignKey("contests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_score", sa.Integer(), nullable=False, server_default="100"),
    )
    op.create_index("ix_contest_tasks_contest_id", "contest_tasks", ["contest_id"])

    op.create_table(
        "contest_participations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("contest_id", sa.Integer(), sa.ForeignKey("contests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("solved_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_ac_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("contest_id", "user_id", name="uq_contest_participation"),
    )
    op.create_index("ix_contest_participations_contest_id", "contest_participations", ["contest_id"])

    # ── Ratings ───────────────────────────────────────────────────────────────
    op.create_table(
        "user_ratings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("rating", sa.Integer(), nullable=False, server_default="1200"),
        sa.Column("solved_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contests_participated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "rating_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("old_rating", sa.Integer(), nullable=False),
        sa.Column("new_rating", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_rating_history_user_id", "rating_history", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_rating_history_user_id", table_name="rating_history")
    op.drop_table("rating_history")
    op.drop_table("user_ratings")

    op.drop_index("ix_contest_participations_contest_id", table_name="contest_participations")
    op.drop_table("contest_participations")
    op.drop_index("ix_contest_tasks_contest_id", table_name="contest_tasks")
    op.drop_table("contest_tasks")
    op.drop_table("contests")
    op.execute("DROP TYPE IF EXISTS conteststatus")

    op.drop_index("ix_user_achievements_user_id", table_name="user_achievements")
    op.drop_table("user_achievements")
    op.drop_table("achievements")
