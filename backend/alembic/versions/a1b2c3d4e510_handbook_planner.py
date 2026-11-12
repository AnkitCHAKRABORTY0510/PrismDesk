"""handbook planner: personal pins, to-dos and reminders on calendar days

Revision ID: a1b2c3d4e510
Revises: a1b2c3d4e509
Create Date: 2026-11-11 19:30:00

Additive: three new tables, no changes to existing data.
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e510"
down_revision = "a1b2c3d4e509"
branch_labels = None
depends_on = None


def _timestamps():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "handbook_pins",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("pin_date", sa.Date(), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=20), server_default="other", nullable=False),
        sa.Column("note", sa.Text(), server_default="", nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "category IN ('deadline', 'meeting', 'milestone', 'idea', 'other')",
            name="ck_handbook_pins_category",
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_handbook_pins_owner_date", "handbook_pins", ["owner_id", "pin_date"])

    op.create_table(
        "handbook_todos",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("todo_date", sa.Date(), nullable=False),
        sa.Column("text", sa.String(length=500), nullable=False),
        sa.Column("done", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_handbook_todos_owner_date", "handbook_todos", ["owner_id", "todo_date"])

    op.create_table(
        "handbook_reminders",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("reminder_date", sa.Date(), nullable=False),
        sa.Column("remind_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=False),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_handbook_reminders_owner_date", "handbook_reminders", ["owner_id", "reminder_date"])
    op.create_index("ix_handbook_reminders_owner_remind_at", "handbook_reminders", ["owner_id", "remind_at"])


def downgrade() -> None:
    op.drop_index("ix_handbook_reminders_owner_remind_at", table_name="handbook_reminders")
    op.drop_index("ix_handbook_reminders_owner_date", table_name="handbook_reminders")
    op.drop_table("handbook_reminders")
    op.drop_index("ix_handbook_todos_owner_date", table_name="handbook_todos")
    op.drop_table("handbook_todos")
    op.drop_index("ix_handbook_pins_owner_date", table_name="handbook_pins")
    op.drop_table("handbook_pins")
