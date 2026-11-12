"""Notification outbox.

Business services call :func:`enqueue_notification` inside their own
transaction. The row is written in a SAVEPOINT and every error is
swallowed, so a notification problem can never fail or roll back the
operation that triggered it. A separate worker process
(``app.workers.notification_worker``) delivers queued rows to Discord.
"""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.notification import (
    NOTIFICATION_CATEGORIES,
    DiscordAccount,
    Notification,
    NotificationPreference,
)

logger = logging.getLogger("prism.notifications")


def category_enabled(db: Session, user_id: UUID, category: str) -> bool:
    preference = db.get(NotificationPreference, (user_id, category))
    return preference.enabled if preference else True


def linked_account(db: Session, user_id: UUID) -> DiscordAccount | None:
    return db.scalar(
        select(DiscordAccount).where(DiscordAccount.user_id == user_id, DiscordAccount.status == "linked")
    )


def enqueue_notification(
    db: Session,
    *,
    category: str,
    event_type: str,
    title: str,
    body: str = "",
    dedupe_key: str,
    recipient_id: UUID | None = None,
    channel_id: str | None = None,
    entity_type: str | None = None,
    entity_id: UUID | str | None = None,
    deliver_after: datetime | None = None,
) -> bool:
    """Queue a Discord notification. Returns True when a row was queued.

    ``deliver_after`` holds the message until that (timezone-aware) time:
    it becomes the row's first ``next_attempt_at``, and the worker only
    claims rows whose ``next_attempt_at`` has passed. Omit it to send as
    soon as the worker next polls.
    """

    if deliver_after is not None and deliver_after.tzinfo is None:
        # A naive time would be read in the database's zone; refuse it
        # without breaking the caller, like every other enqueue failure.
        logger.warning("Ignoring notification %s with a naive deliver_after time.", event_type)
        return False

    if category not in NOTIFICATION_CATEGORIES:
        logger.warning("Ignoring notification with unknown category %s", category)
        return False

    try:
        with db.begin_nested():
            if recipient_id is not None:
                # Respect opt-outs and skip users without a linked
                # Discord account; Discord is the only delivery channel.
                if not category_enabled(db, recipient_id, category):
                    return False
                if linked_account(db, recipient_id) is None:
                    return False

            result = db.execute(
                insert(Notification)
                .values(
                    recipient_id=recipient_id,
                    channel_id=channel_id,
                    category=category,
                    event_type=event_type,
                    title=title[:200],
                    body=body[:2000],
                    entity_type=entity_type,
                    entity_id=str(entity_id) if entity_id is not None else None,
                    dedupe_key=dedupe_key[:255],
                    max_attempts=settings.NOTIFICATION_MAX_ATTEMPTS,
                    # Without a time the column's server default (now()) applies.
                    **({"next_attempt_at": deliver_after} if deliver_after is not None else {}),
                )
                .on_conflict_do_nothing(index_elements=["dedupe_key"])
                .returning(Notification.id)
            )
            return result.scalar_one_or_none() is not None
    except Exception:
        logger.exception("Failed to queue notification %s; continuing without it.", event_type)
        return False


def retry_delay(attempt_number: int) -> timedelta:
    """Exponential backoff: base * 2^(attempt-1), capped."""

    seconds = settings.NOTIFICATION_RETRY_BASE_SECONDS * (2 ** max(attempt_number - 1, 0))
    return timedelta(seconds=min(seconds, settings.NOTIFICATION_RETRY_MAX_SECONDS))


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
