"""Consolidated migrations 003-010

Revision ID: 011
Revises: 001
Create Date: 2026-06-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "011"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── courses: extend (003) ──────────────────────────────────────────────
    op.add_column("courses", sa.Column("slug", sa.String(255), nullable=True))
    op.add_column("courses", sa.Column("short_description", sa.String(500), nullable=True))
    op.add_column("courses", sa.Column("cover_image_url", sa.String(500), nullable=True))
    op.add_column("courses", sa.Column("sort_order", sa.Integer(), server_default="0"))
    op.add_column("courses", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.add_column("courses", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("courses", "description", existing_type=sa.String(2000), type_=sa.Text(), existing_nullable=True)
    op.create_index("ix_courses_slug", "courses", ["slug"], unique=True)

    # ── users: extend (008) ────────────────────────────────────────────────
    op.add_column("users", sa.Column("email", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("full_name", sa.String(255), nullable=True))
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── task_tests: extend (009, 010) ──────────────────────────────────────
    op.add_column("task_tests", sa.Column("verification_sql", sa.Text(), nullable=True))
    op.add_column("task_tests", sa.Column("test_files", sa.JSON(), nullable=True))

    # ── new enums (003, 005) ───────────────────────────────────────────────
    op.execute("CREATE TYPE coursenodetype AS ENUM ('module', 'submodule', 'topic', 'subtopic')")
    op.execute("CREATE TYPE node_task_progress_status AS ENUM ('not_started', 'in_progress', 'completed')")

    # ── course_nodes (004 + 005: final schema uses coursestatus) ──────────
    op.execute("""
        CREATE TABLE course_nodes (
            id           SERIAL PRIMARY KEY,
            course_id    INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
            parent_id    INTEGER REFERENCES course_nodes(id) ON DELETE CASCADE,
            type         coursenodetype NOT NULL,
            title        VARCHAR(255) NOT NULL,
            description  TEXT,
            content      TEXT,
            sort_order   INTEGER NOT NULL DEFAULT 0,
            status       coursestatus NOT NULL DEFAULT 'draft',
            is_published BOOLEAN NOT NULL DEFAULT false,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            archived_at  TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX ix_course_nodes_course_id ON course_nodes(course_id)")
    op.execute("CREATE INDEX ix_course_nodes_parent_id ON course_nodes(parent_id)")
    op.execute("CREATE INDEX ix_course_nodes_course_parent_sort ON course_nodes(course_id, parent_id, sort_order)")

    # ── course_node_tasks (005) ────────────────────────────────────────────
    op.execute("""
        CREATE TABLE course_node_tasks (
            id          SERIAL PRIMARY KEY,
            node_id     INTEGER NOT NULL REFERENCES course_nodes(id) ON DELETE CASCADE,
            task_id     INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            sort_order  INTEGER NOT NULL DEFAULT 0,
            is_required BOOLEAN NOT NULL DEFAULT true,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_course_node_tasks_node_task UNIQUE (node_id, task_id)
        )
    """)
    op.execute("CREATE INDEX ix_course_node_tasks_node_sort ON course_node_tasks(node_id, sort_order)")

    # ── user_course_progress (005 final schema) ────────────────────────────
    op.execute("""
        CREATE TABLE user_course_progress (
            id                    SERIAL PRIMARY KEY,
            user_id               INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            course_id             INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
            progress_percent      FLOAT NOT NULL DEFAULT 0.0,
            completed_tasks_count INTEGER NOT NULL DEFAULT 0,
            total_tasks_count     INTEGER NOT NULL DEFAULT 0,
            current_node_id       INTEGER REFERENCES course_nodes(id) ON DELETE SET NULL,
            last_task_id          INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
            updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ix_user_course_progress_user_course UNIQUE (user_id, course_id)
        )
    """)

    # ── user_course_node_task_progress (005) ───────────────────────────────
    op.execute("""
        CREATE TABLE user_course_node_task_progress (
            id                 SERIAL PRIMARY KEY,
            user_id            INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            node_task_id       INTEGER NOT NULL REFERENCES course_node_tasks(id) ON DELETE CASCADE,
            status             node_task_progress_status NOT NULL DEFAULT 'not_started',
            best_submission_id INTEGER REFERENCES submissions(id) ON DELETE SET NULL,
            completed_at       TIMESTAMPTZ,
            updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ix_user_course_node_task_progress_user_node_task UNIQUE (user_id, node_task_id)
        )
    """)

    # ── user_course_enrollments (006) ──────────────────────────────────────
    op.create_table(
        "user_course_enrollments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "course_id", name="uq_user_course_enrollment"),
    )
    op.create_index("ix_user_course_enrollments_user_id", "user_course_enrollments", ["user_id"])
    op.create_index("ix_user_course_enrollments_course_id", "user_course_enrollments", ["course_id"])

    # ── platform_settings (007) ────────────────────────────────────────────
    op.create_table(
        "platform_settings",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.Text(), server_default="", nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )

    # ── password_reset_tokens (008) ────────────────────────────────────────
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), server_default="false", nullable=False),
    )
    op.create_index("ix_password_reset_tokens_token", "password_reset_tokens", ["token"])


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_token", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")

    op.drop_table("platform_settings")

    op.drop_index("ix_user_course_enrollments_course_id", table_name="user_course_enrollments")
    op.drop_index("ix_user_course_enrollments_user_id", table_name="user_course_enrollments")
    op.drop_table("user_course_enrollments")

    op.execute("DROP TABLE IF EXISTS user_course_node_task_progress")
    op.execute("DROP TABLE IF EXISTS user_course_progress")
    op.execute("DROP INDEX IF EXISTS ix_course_node_tasks_node_sort")
    op.execute("DROP TABLE IF EXISTS course_node_tasks")
    op.execute("DROP INDEX IF EXISTS ix_course_nodes_course_parent_sort")
    op.execute("DROP INDEX IF EXISTS ix_course_nodes_parent_id")
    op.execute("DROP INDEX IF EXISTS ix_course_nodes_course_id")
    op.execute("DROP TABLE IF EXISTS course_nodes")

    op.execute("DROP TYPE IF EXISTS node_task_progress_status")
    op.execute("DROP TYPE IF EXISTS coursenodetype")

    op.drop_column("task_tests", "test_files")
    op.drop_column("task_tests", "verification_sql")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_column("users", "full_name")
    op.drop_column("users", "email")

    op.drop_index("ix_courses_slug", table_name="courses")
    op.drop_column("courses", "archived_at")
    op.drop_column("courses", "updated_at")
    op.drop_column("courses", "sort_order")
    op.drop_column("courses", "cover_image_url")
    op.drop_column("courses", "short_description")
    op.drop_column("courses", "slug")
    op.alter_column("courses", "description", existing_type=sa.Text(), type_=sa.String(2000), existing_nullable=True)
