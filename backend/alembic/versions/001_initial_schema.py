"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("login", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("admin", "student", name="userrole"), nullable=False, server_default="student"),
        sa.Column("status", sa.Enum("active", "blocked", "archived", name="userstatus"), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "courses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.String(2000), nullable=True),
        sa.Column("status", sa.Enum("draft", "published", "archived", name="coursestatus"), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "modules",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("course_id", sa.Integer, sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("order_index", sa.Integer, server_default="0"),
    )

    op.create_table(
        "submodules",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("module_id", sa.Integer, sa.ForeignKey("modules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("order_index", sa.Integer, server_default="0"),
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("submodule_id", sa.Integer, sa.ForeignKey("submodules.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("task_type", sa.Enum("python_io", "python_oop", "python_numpy", "sql_query", name="tasktype"), nullable=False),
        sa.Column("runner_type", sa.Enum("stdin_runner", "pytest_runner", "sql_runner", name="runnertype"), nullable=False),
        sa.Column("status", sa.Enum("draft", "published", "archived", name="taskstatus"), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("sql_schema", sa.Text, nullable=True),
        sa.Column("sql_seed", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "task_tests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("task_id", sa.Integer, sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("test_type", sa.Enum("public", "hidden", name="testtype"), nullable=False, server_default="public"),
        sa.Column("input_data", sa.Text, nullable=True),
        sa.Column("expected_output", sa.Text, nullable=True),
        sa.Column("weight", sa.Float, server_default="1.0"),
        sa.Column("order_index", sa.Integer, server_default="0"),
    )

    op.create_table(
        "task_hints",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("task_id", sa.Integer, sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hint_level", sa.Integer, server_default="1"),
        sa.Column("unlock_attempts", sa.Integer, server_default="3"),
        sa.Column("content", sa.Text, nullable=False),
    )

    op.create_table(
        "task_lectures",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("task_id", sa.Integer, sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("unlock_attempts", sa.Integer, server_default="0"),
    )

    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("task_id", sa.Integer, sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.Text, nullable=False),
        sa.Column("status", sa.Enum("queued", "running", "finished", name="submissionstatus"), nullable=False, server_default="queued"),
        sa.Column("verdict", sa.Enum("AC", "WA", "RE", "TLE", "MLE", "CE", "PE", "IE", name="verdict"), nullable=True),
        sa.Column("runtime", sa.Float, nullable=True),
        sa.Column("memory", sa.Float, nullable=True),
        sa.Column("error_output", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "submission_tests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("submission_id", sa.Integer, sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("test_id", sa.Integer, sa.ForeignKey("task_tests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("verdict", sa.Enum("AC", "WA", "RE", "TLE", "MLE", "CE", "PE", "IE", name="verdict", create_type=False), nullable=True),
        sa.Column("runtime", sa.Float, nullable=True),
        sa.Column("actual_output", sa.Text, nullable=True),
    )

    op.create_table(
        "student_progress",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.Integer, sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempts", sa.Integer, server_default="0"),
        sa.Column("best_verdict", sa.String(10), nullable=True),
        sa.Column("solved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_submission_id", sa.Integer, sa.ForeignKey("submissions.id", ondelete="SET NULL"), nullable=True),
    )

    op.create_table(
        "personal_links",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("task_id", sa.Integer, sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("usage_limit", sa.Integer, nullable=True),
        sa.Column("usage_count", sa.Integer, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("personal_links")
    op.drop_table("student_progress")
    op.drop_table("submission_tests")
    op.drop_table("submissions")
    op.drop_table("task_lectures")
    op.drop_table("task_hints")
    op.drop_table("task_tests")
    op.drop_table("tasks")
    op.drop_table("submodules")
    op.drop_table("modules")
    op.drop_table("courses")
    op.drop_table("users")
    for name in ["verdict", "submissionstatus", "testtype", "taskstatus", "runnertype", "tasktype", "coursestatus", "userstatus", "userrole"]:
        op.execute(f"DROP TYPE IF EXISTS {name}")
