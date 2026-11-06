"""phase 7: Discord accounts, preferences and notification outbox

Revision ID: a1b2c3d4e507
Revises: a1b2c3d4e506
Create Date: 2026-11-06 15:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e507"
down_revision = "a1b2c3d4e506"
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
        "discord_accounts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("discord_user_id", sa.String(length=32), nullable=False),
        sa.Column("discord_username", sa.String(length=100), nullable=False),
        sa.Column("dm_channel_id", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="linked", nullable=False),
        _ts("linked_at"),
        _ts("unlinked_at", nullable=True, default=False),
        _ts("updated_at"),
        sa.CheckConstraint("status IN ('linked', 'unlinked')", name="ck_discord_accounts_status"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(
        "uq_discord_accounts_discord_user_linked",
        "discord_accounts",
        ["discord_user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'linked'"),
    )

    op.create_table(
        "discord_oauth_states",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("state_hash", sa.String(length=64), nullable=False),
        _ts("expires_at", default=False),
        _ts("used_at", nullable=True, default=False),
        _ts("created_at"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state_hash"),
    )

    op.create_table(
        "notification_preferences",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        _ts("updated_at"),
        sa.CheckConstraint(
            "category IN ('tasks', 'projects', 'conferences', 'handbook', 'administrative')",
            name="ck_notification_preferences_category",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "category"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("recipient_id", sa.UUID(), nullable=True),
        sa.Column("channel_id", sa.String(length=32), nullable=True),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.String(length=2000), server_default="", nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=True),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="5", nullable=False),
        _ts("next_attempt_at"),
        _ts("last_attempt_at", nullable=True, default=False),
        _ts("sent_at", nullable=True, default=False),
        sa.Column("last_error", sa.String(length=1000), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'sent', 'failed', 'retry_scheduled')",
            name="ck_notifications_status",
        ),
        sa.CheckConstraint(
            "recipient_id IS NOT NULL OR channel_id IS NOT NULL", name="ck_notifications_destination"
        ),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key"),
    )
    op.create_index("ix_notifications_status_next_attempt", "notifications", ["status", "next_attempt_at"])
    op.create_index("ix_notifications_recipient_created", "notifications", ["recipient_id", "created_at"])

    op.create_table(
        "notification_delivery_attempts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("notification_id", sa.UUID(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("error", sa.String(length=1000), nullable=True),
        _ts("attempted_at"),
        sa.ForeignKeyConstraint(["notification_id"], ["notifications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notification_delivery_attempts_notification", "notification_delivery_attempts", ["notification_id"]
    )


def downgrade() -> None:
    op.drop_table("notification_delivery_attempts")
    op.drop_table("notifications")
    op.drop_table("notification_preferences")
    op.drop_table("discord_oauth_states")
    op.drop_index("uq_discord_accounts_discord_user_linked", table_name="discord_accounts")
    op.drop_table("discord_accounts")
