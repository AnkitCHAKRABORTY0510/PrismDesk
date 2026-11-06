"""phase 4: tasks, assignments, versioned submissions and reviews

Revision ID: a1b2c3d4e504
Revises: a1b2c3d4e503
Create Date: 2026-11-06 13:30:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a1b2c3d4e504"
down_revision = "a1b2c3d4e503"
branch_labels = None
depends_on = None


def _ts(name, nullable=False, default=True):
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        server_default=sa.text("now()") if default else None,
        nullable=nullable,
    )


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("task_type", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("priority", sa.String(length=10), server_default="medium", nullable=False),
        _ts("due_at", nullable=True, default=False),
        _ts("created_at"),
        _ts("updated_at"),
        sa.CheckConstraint("task_type IN ('official', 'personal')", name="ck_tasks_type"),
        sa.CheckConstraint("priority IN ('low', 'medium', 'high', 'urgent')", name="ck_tasks_priority"),
        sa.CheckConstraint(
            "task_type = 'personal' OR project_id IS NOT NULL", name="ck_tasks_official_has_project"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"])
    op.create_index("ix_tasks_created_by", "tasks", ["created_by"])
    op.create_index("ix_tasks_due_at", "tasks", ["due_at"])

    op.create_table(
        "task_assignments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("assignee_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="todo", nullable=False),
        sa.Column("assigned_by", sa.UUID(), nullable=True),
        _ts("assigned_at"),
        _ts("submitted_at", nullable=True, default=False),
        _ts("completed_at", nullable=True, default=False),
        _ts("updated_at"),
        sa.CheckConstraint(
            "status IN ('todo', 'in_progress', 'under_review', 'revision_required', 'completed')",
            name="ck_task_assignments_status",
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "assignee_id", name="uq_task_assignments_task_assignee"),
    )
    op.create_index("ix_task_assignments_assignee_status", "task_assignments", ["assignee_id", "status"])

    op.create_table(
        "task_submissions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("assignment_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("response_text", sa.Text(), server_default="", nullable=False),
        sa.Column("links", postgresql.ARRAY(sa.String(length=2048)), server_default="{}", nullable=False),
        sa.Column("submitted_by", sa.UUID(), nullable=True),
        _ts("submitted_at"),
        sa.ForeignKeyConstraint(["assignment_id"], ["task_assignments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submitted_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assignment_id", "version", name="uq_task_submissions_assignment_version"),
    )

    op.create_table(
        "task_reviews",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("submission_id", sa.UUID(), nullable=False),
        sa.Column("reviewer_id", sa.UUID(), nullable=True),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("feedback", sa.Text(), server_default="", nullable=False),
        _ts("created_at"),
        sa.CheckConstraint(
            "decision IN ('approved', 'revision_required')", name="ck_task_reviews_decision"
        ),
        sa.ForeignKeyConstraint(["submission_id"], ["task_submissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_reviews_submission_id", "task_reviews", ["submission_id"])


def downgrade() -> None:
    op.drop_table("task_reviews")
    op.drop_table("task_submissions")
    op.drop_table("task_assignments")
    op.drop_table("tasks")
