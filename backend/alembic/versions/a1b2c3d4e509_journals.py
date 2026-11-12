"""journals: per-user journal list with optional special-issue deadline

Revision ID: a1b2c3d4e509
Revises: a1b2c3d4e508
Create Date: 2026-11-11 18:30:00

Additive: one new table, no changes to existing data.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a1b2c3d4e509"
down_revision = "a1b2c3d4e508"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "journals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("title_key", sa.String(length=300), nullable=False),
        sa.Column("issn", sa.String(length=9), nullable=True),
        sa.Column("publisher", sa.String(length=300), nullable=True),
        sa.Column("homepage_url", sa.String(length=2048), nullable=True),
        sa.Column("sjr_quartile", sa.String(length=2), nullable=True),
        sa.Column("sjr", sa.Float(), nullable=True),
        sa.Column("h_index", sa.Integer(), nullable=True),
        sa.Column("subject_areas", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("is_open_access", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
        sa.Column("special_issue_title", sa.String(length=300), nullable=True),
        sa.Column("submission_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_journals_owner_title", "journals", ["owner_id", "title_key"], unique=True)
    op.create_index(
        "uq_journals_owner_issn",
        "journals",
        ["owner_id", "issn"],
        unique=True,
        postgresql_where=sa.text("issn IS NOT NULL"),
    )
    op.create_index("ix_journals_owner_deadline", "journals", ["owner_id", "submission_deadline"])


def downgrade() -> None:
    op.drop_index("ix_journals_owner_deadline", table_name="journals")
    op.drop_index("uq_journals_owner_issn", table_name="journals")
    op.drop_index("uq_journals_owner_title", table_name="journals")
    op.drop_table("journals")
