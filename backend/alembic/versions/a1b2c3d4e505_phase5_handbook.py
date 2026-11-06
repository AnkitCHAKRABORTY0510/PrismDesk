"""phase 5: research handbook entries, summaries, versions and comments

Revision ID: a1b2c3d4e505
Revises: a1b2c3d4e504
Create Date: 2026-11-06 14:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a1b2c3d4e505"
down_revision = "a1b2c3d4e504"
branch_labels = None
depends_on = None


def _ts(name):
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False)


def _text(name):
    return sa.Column(name, sa.Text(), server_default="", nullable=False)


def upgrade() -> None:
    op.create_table(
        "handbook_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        _text("work_completed"),
        _text("research_progress"),
        _text("problems"),
        _text("next_steps"),
        sa.Column("references", postgresql.ARRAY(sa.String(length=2048)), server_default="{}", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "student_id", "project_id", "entry_date", name="uq_handbook_entries_student_project_date"
        ),
    )
    op.create_index("ix_handbook_entries_project_date", "handbook_entries", ["project_id", "entry_date"])

    op.create_table(
        "handbook_entry_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("entry_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("edited_by", sa.UUID(), nullable=True),
        _ts("edited_at"),
        sa.ForeignKeyConstraint(["entry_id"], ["handbook_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["edited_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entry_id", "version", name="uq_handbook_entry_versions_entry_version"),
    )

    op.create_table(
        "daily_summaries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        _text("challenges"),
        _text("plan_next"),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "entry_date", name="uq_daily_summaries_student_date"),
    )

    op.create_table(
        "daily_summary_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("summary_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        _ts("edited_at"),
        sa.ForeignKeyConstraint(["summary_id"], ["daily_summaries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("summary_id", "version", name="uq_daily_summary_versions_summary_version"),
    )

    op.create_table(
        "handbook_comments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("entry_id", sa.UUID(), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("author_id", sa.UUID(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["entry_id"], ["handbook_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["handbook_comments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_handbook_comments_entry_id", "handbook_comments", ["entry_id"])
    op.create_index("ix_handbook_comments_parent_id", "handbook_comments", ["parent_id"])


def downgrade() -> None:
    op.drop_table("handbook_comments")
    op.drop_table("daily_summary_versions")
    op.drop_table("daily_summaries")
    op.drop_table("handbook_entry_versions")
    op.drop_table("handbook_entries")
