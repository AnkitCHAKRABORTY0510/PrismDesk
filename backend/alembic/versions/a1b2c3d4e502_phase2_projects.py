"""phase 2: projects and project membership

Revision ID: a1b2c3d4e502
Revises: a1b2c3d4e501
Create Date: 2026-11-06 12:30:00
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e502"
down_revision = "a1b2c3d4e501"
branch_labels = None
depends_on = None


def _ts(name, nullable=True, default=False):
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        server_default=sa.text("now()") if default else None,
        nullable=nullable,
    )


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("objectives", sa.Text(), server_default="", nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("archive_requested_by", sa.UUID(), nullable=True),
        _ts("archive_requested_at"),
        sa.Column("archive_request_reason", sa.String(length=500), nullable=True),
        sa.Column("archived_by", sa.UUID(), nullable=True),
        _ts("archived_at"),
        sa.Column("deleted_by", sa.UUID(), nullable=True),
        _ts("deleted_at"),
        _ts("created_at", nullable=False, default=True),
        _ts("updated_at", nullable=False, default=True),
        sa.CheckConstraint("status IN ('active', 'archived', 'deleted')", name="ck_projects_status"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["archive_requested_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["archived_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["deleted_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_status", "projects", ["status"])
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])

    op.create_table(
        "project_members",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("membership_role", sa.String(length=20), nullable=False),
        sa.Column("membership_status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("added_by", sa.UUID(), nullable=True),
        _ts("joined_at", nullable=False, default=True),
        _ts("removed_at"),
        _ts("updated_at", nullable=False, default=True),
        sa.CheckConstraint(
            "membership_role IN ('owner', 'supervisor', 'member', 'guest')",
            name="ck_project_members_role",
        ),
        sa.CheckConstraint(
            "membership_status IN ('active', 'removed')",
            name="ck_project_members_status",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["added_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
    )
    op.create_index("ix_project_members_user_id", "project_members", ["user_id"])


def downgrade() -> None:
    op.drop_table("project_members")
    op.drop_table("projects")
