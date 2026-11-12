"""discord project channels: one private Discord channel per project

Revision ID: a1b2c3d4e512
Revises: a1b2c3d4e511
Create Date: 2026-11-12 01:40:00

Additive: one new table, no changes to existing data.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a1b2c3d4e512"
down_revision = "a1b2c3d4e511"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "discord_project_channels",
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("channel_id", sa.String(length=32), nullable=False),
        sa.Column("channel_name", sa.String(length=100), nullable=False),
        sa.Column(
            "member_discord_ids",
            postgresql.ARRAY(sa.String(length=32)),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("access_mode", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("access_mode IN ('active', 'read_only')", name="ck_discord_project_channels_mode"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("project_id"),
        sa.UniqueConstraint("channel_id"),
    )


def downgrade() -> None:
    op.drop_table("discord_project_channels")
