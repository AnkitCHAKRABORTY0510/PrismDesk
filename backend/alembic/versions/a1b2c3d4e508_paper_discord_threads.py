"""paper Discord discussion threads and research notification category

Revision ID: a1b2c3d4e508
Revises: a1b2c3d4e507
Create Date: 2026-11-06 17:00:00

Additive: one nullable column; the preference category check gains 'research'.
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e508"
down_revision = "a1b2c3d4e507"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("research_papers", sa.Column("discord_thread_id", sa.String(length=32), nullable=True))
    op.drop_constraint("ck_notification_preferences_category", "notification_preferences", type_="check")
    op.create_check_constraint(
        "ck_notification_preferences_category",
        "notification_preferences",
        "category IN ('tasks', 'projects', 'research', 'conferences', 'handbook', 'administrative')",
    )


def downgrade() -> None:
    op.execute("DELETE FROM notification_preferences WHERE category = 'research'")
    op.drop_constraint("ck_notification_preferences_category", "notification_preferences", type_="check")
    op.create_check_constraint(
        "ck_notification_preferences_category",
        "notification_preferences",
        "category IN ('tasks', 'projects', 'conferences', 'handbook', 'administrative')",
    )
    op.drop_column("research_papers", "discord_thread_id")
