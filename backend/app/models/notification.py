import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.models.columns import created_at, optional_timestamp, updated_at, uuid_pk

NOTIFICATION_CATEGORIES = ("tasks", "projects", "conferences", "handbook", "administrative")
NOTIFICATION_STATUSES = ("pending", "processing", "sent", "failed", "retry_scheduled")


class DiscordAccount(Base):
    """Verified link between a Prism Desk user and a Discord user ID.

    Only the public Discord identifier and username are stored. OAuth
    access tokens are used once during linking and discarded.
    """

    __tablename__ = "discord_accounts"

    __table_args__ = (
        Index(
            "uq_discord_accounts_discord_user_linked",
            "discord_user_id",
            unique=True,
            postgresql_where=text("status = 'linked'"),
        ),
        CheckConstraint("status IN ('linked', 'unlinked')", name="ck_discord_accounts_status"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    discord_user_id: Mapped[str] = mapped_column(String(32), nullable=False)
    discord_username: Mapped[str] = mapped_column(String(100), nullable=False)
    dm_channel_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="linked", server_default="linked")
    linked_at: Mapped[datetime] = created_at()
    unlinked_at: Mapped[datetime | None] = optional_timestamp()
    updated_at: Mapped[datetime] = updated_at()


class DiscordOAuthState(Base):
    """One-time OAuth2 state values (stored hashed) bound to a user."""

    __tablename__ = "discord_oauth_states"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    state_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = optional_timestamp()
    created_at: Mapped[datetime] = created_at()


class NotificationPreference(Base):
    """Opt-out switches; a missing row means the category is enabled."""

    __tablename__ = "notification_preferences"

    __table_args__ = (
        CheckConstraint(
            "category IN ('tasks', 'projects', 'conferences', 'handbook', 'administrative')",
            name="ck_notification_preferences_category",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    category: Mapped[str] = mapped_column(String(30), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    updated_at: Mapped[datetime] = updated_at()


class Notification(Base):
    """Outbox row delivered to Discord by the notification worker."""

    __tablename__ = "notifications"

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'sent', 'failed', 'retry_scheduled')",
            name="ck_notifications_status",
        ),
        CheckConstraint(
            "recipient_id IS NOT NULL OR channel_id IS NOT NULL",
            name="ck_notifications_destination",
        ),
        Index("ix_notifications_status_next_attempt", "status", "next_attempt_at"),
        Index("ix_notifications_recipient_created", "recipient_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    recipient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    channel_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(String(2000), nullable=False, default="", server_default="")
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dedupe_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=5, server_default="5")
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_attempt_at: Mapped[datetime | None] = optional_timestamp()
    sent_at: Mapped[datetime | None] = optional_timestamp()
    last_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()


class NotificationDeliveryAttempt(Base):
    __tablename__ = "notification_delivery_attempts"

    __table_args__ = (Index("ix_notification_delivery_attempts_notification", "notification_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    notification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    attempted_at: Mapped[datetime] = created_at()
