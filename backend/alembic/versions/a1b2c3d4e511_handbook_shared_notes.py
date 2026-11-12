"""handbook shared notes: a per-day note students share with their supervisors

Revision ID: a1b2c3d4e511
Revises: a1b2c3d4e510
Create Date: 2026-11-11 20:15:00

Additive: three new tables, no changes to existing data.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a1b2c3d4e511"
down_revision = "a1b2c3d4e510"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "handbook_shared_notes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "entry_date", name="uq_handbook_shared_notes_student_date"),
    )
    op.create_index("ix_handbook_shared_notes_date", "handbook_shared_notes", ["entry_date"])

    op.create_table(
        "handbook_shared_note_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("note_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["note_id"], ["handbook_shared_notes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("note_id", "version", name="uq_handbook_shared_note_versions_note_version"),
    )

    op.create_table(
        "handbook_shared_note_comments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("note_id", sa.UUID(), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("author_id", sa.UUID(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["note_id"], ["handbook_shared_notes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["handbook_shared_note_comments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_handbook_shared_note_comments_note_id", "handbook_shared_note_comments", ["note_id"])
    op.create_index("ix_handbook_shared_note_comments_parent_id", "handbook_shared_note_comments", ["parent_id"])


def downgrade() -> None:
    op.drop_index("ix_handbook_shared_note_comments_parent_id", table_name="handbook_shared_note_comments")
    op.drop_index("ix_handbook_shared_note_comments_note_id", table_name="handbook_shared_note_comments")
    op.drop_table("handbook_shared_note_comments")
    op.drop_table("handbook_shared_note_versions")
    op.drop_index("ix_handbook_shared_notes_date", table_name="handbook_shared_notes")
    op.drop_table("handbook_shared_notes")
