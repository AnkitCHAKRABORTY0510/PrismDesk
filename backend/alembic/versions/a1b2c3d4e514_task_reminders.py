"""task reminders: a third task type that points at another task

Revision ID: a1b2c3d4e514
Revises: a1b2c3d4e513
Create Date: 2026-11-12 03:00:00

Additive: widens the tasks.task_type check to allow 'reminder' and adds a
nullable tasks.related_task_id. Existing rows are unchanged.
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e514"
down_revision = "a1b2c3d4e513"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_tasks_type", "tasks", type_="check")
    op.create_check_constraint("ck_tasks_type", "tasks", "task_type IN ('official', 'personal', 'reminder')")
    op.add_column("tasks", sa.Column("related_task_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_tasks_related_task_id_tasks", "tasks", "tasks", ["related_task_id"], ["id"], ondelete="CASCADE"
    )
    op.create_index("ix_tasks_related_task_id", "tasks", ["related_task_id"])


def downgrade() -> None:
    op.execute("DELETE FROM tasks WHERE task_type = 'reminder'")
    op.drop_index("ix_tasks_related_task_id", table_name="tasks")
    op.drop_constraint("fk_tasks_related_task_id_tasks", "tasks", type_="foreignkey")
    op.drop_column("tasks", "related_task_id")
    op.drop_constraint("ck_tasks_type", "tasks", type_="check")
    op.create_check_constraint("ck_tasks_type", "tasks", "task_type IN ('official', 'personal')")
