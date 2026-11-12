"""project repo links: GitHub repository links on projects

Revision ID: a1b2c3d4e513
Revises: a1b2c3d4e512
Create Date: 2026-11-12 09:00:00

Additive: one new table, no changes to existing data.
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e513"
down_revision = "a1b2c3d4e512"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_repo_links",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=True),
        sa.Column("added_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["added_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "url", name="uq_project_repo_links_project_url"),
    )
    op.create_index("ix_project_repo_links_project_id", "project_repo_links", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_project_repo_links_project_id", table_name="project_repo_links")
    op.drop_table("project_repo_links")
