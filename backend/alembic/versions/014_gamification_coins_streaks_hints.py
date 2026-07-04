"""Coins, streaks, task rewards and coin-gated hints

Revision ID: 014
Revises: 013
Create Date: 2026-07-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("reward_coins", sa.Integer(), nullable=False, server_default="10"))
    op.add_column("task_hints", sa.Column("coin_cost", sa.Integer(), nullable=False, server_default="30"))

    op.create_table(
        "coin_wallets",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "coin_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_coin_transactions_user_id", "coin_transactions", ["user_id"])

    op.create_table(
        "student_streaks",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("current_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_active_date", sa.Date(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "student_hint_unlocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hint_id", sa.Integer(), sa.ForeignKey("task_hints.id", ondelete="CASCADE"), nullable=False),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "hint_id", name="uq_student_hint_unlock"),
    )
    op.create_index("ix_student_hint_unlocks_user_id", "student_hint_unlocks", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_student_hint_unlocks_user_id", table_name="student_hint_unlocks")
    op.drop_table("student_hint_unlocks")
    op.drop_table("student_streaks")
    op.drop_index("ix_coin_transactions_user_id", table_name="coin_transactions")
    op.drop_table("coin_transactions")
    op.drop_table("coin_wallets")
    op.drop_column("task_hints", "coin_cost")
    op.drop_column("tasks", "reward_coins")
