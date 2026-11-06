"""phase 6: conferences and project associations

Revision ID: a1b2c3d4e506
Revises: a1b2c3d4e505
Create Date: 2026-11-06 14:30:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a1b2c3d4e506"
down_revision = "a1b2c3d4e505"
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
        "conferences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("acronym", sa.String(length=50), nullable=True),
        sa.Column("website_url", sa.String(length=2048), nullable=True),
        sa.Column("cfp_url", sa.String(length=2048), nullable=True),
        _ts("submission_deadline", default=False),
        sa.Column(
            "important_dates", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False
        ),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
        sa.Column("added_by", sa.UUID(), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.ForeignKeyConstraint(["added_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_conferences_name_deadline",
        "conferences",
        [sa.literal_column("lower(name)"), "submission_deadline"],
        unique=True,
    )
    op.create_index("ix_conferences_submission_deadline", "conferences", ["submission_deadline"])

    op.create_table(
        "project_conferences",
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("conference_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("added_by", sa.UUID(), nullable=True),
        _ts("added_at"),
        sa.Column("archived_by", sa.UUID(), nullable=True),
        _ts("archived_at", nullable=True, default=False),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_project_conferences_status"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conference_id"], ["conferences.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["added_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["archived_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("project_id", "conference_id"),
    )
    op.create_index("ix_project_conferences_conference_id", "project_conferences", ["conference_id"])


def downgrade() -> None:
    op.drop_table("project_conferences")
    op.drop_index("uq_conferences_name_deadline", table_name="conferences")
    op.drop_table("conferences")
