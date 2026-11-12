"""Deliver handbook planner reminders as Discord DMs.

Handbook reminders (``HandbookReminder``) are owned by one user and carry a
``remind_at`` time. The notification worker calls :func:`dispatch_due_reminders`
on every poll; it queues each reminder that falls inside a short look-ahead
window as a *scheduled* outbox row (``deliver_after=remind_at``), so the DM
goes out on time instead of on the next scan.

This module only reads handbook tables. Queuing is idempotent: the dedupe key
contains the reminder id and its ``remind_at``, so re-scans never duplicate a
message, and moving a reminder to a new time queues a fresh one. Just before
sending, the worker calls :func:`cancel_reason` so a reminder that was
deleted, dismissed or moved after it was queued is not delivered.
"""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.handbook import HandbookReminder
from app.models.notification import DiscordAccount, Notification, NotificationPreference
from app.services.notification_service import enqueue_notification, now_utc

EVENT_TYPE = "handbook.reminder"
ENTITY_TYPE = "handbook_reminder"
CATEGORY = "handbook"

# Queue reminders this far ahead; the worker polls far more often than this,
# so every reminder is queued before it is due and then held until remind_at.
LOOKAHEAD = timedelta(minutes=10)
# Reminders missed while the worker was down are still sent if they are at
# most this late; older ones are skipped rather than arriving hours late.
GRACE = timedelta(hours=1)


def dedupe_key(reminder_id: UUID, remind_at: datetime) -> str:
    return f"{EVENT_TYPE}:{reminder_id}:{remind_at.isoformat()}"


def _body(reminder: HandbookReminder) -> str:
    # <t:unix:F> renders in each reader's own timezone inside Discord.
    when = f"<t:{int(reminder.remind_at.timestamp())}:F>"
    return f"{reminder.note}\n\nScheduled for {when} in your Prism Desk planner."


def dispatch_due_reminders(db: Session, now: datetime | None = None) -> int:
    """Queue reminders due between ``now - GRACE`` and ``now + LOOKAHEAD``.

    Returns the number of newly queued notifications and commits.
    """

    now = now or now_utc()
    rows = db.scalars(
        select(HandbookReminder)
        # Only owners who could receive it: linked and not opted out of
        # handbook notifications. enqueue_notification re-checks both.
        .join(
            DiscordAccount,
            and_(DiscordAccount.user_id == HandbookReminder.owner_id, DiscordAccount.status == "linked"),
        )
        .outerjoin(
            NotificationPreference,
            and_(
                NotificationPreference.user_id == HandbookReminder.owner_id,
                NotificationPreference.category == CATEGORY,
            ),
        )
        .where(
            HandbookReminder.dismissed_at.is_(None),
            HandbookReminder.remind_at > now - GRACE,
            HandbookReminder.remind_at <= now + LOOKAHEAD,
            NotificationPreference.enabled.is_not(False),
        )
        .order_by(HandbookReminder.remind_at)
    ).all()

    queued = 0
    for reminder in rows:
        queued += enqueue_notification(
            db,
            recipient_id=reminder.owner_id,
            category=CATEGORY,
            event_type=EVENT_TYPE,
            title="Reminder",
            body=_body(reminder),
            entity_type=ENTITY_TYPE,
            entity_id=reminder.id,
            dedupe_key=dedupe_key(reminder.id, reminder.remind_at),
            deliver_after=reminder.remind_at,
        )
    db.commit()
    return queued


def cancel_reason(db: Session, notification: Notification) -> str | None:
    """Why a queued reminder must not be sent any more, or None to send it."""

    if notification.event_type != EVENT_TYPE or not notification.entity_id:
        return None
    try:
        reminder = db.get(HandbookReminder, UUID(notification.entity_id))
    except ValueError:
        return "Reminder reference is invalid."
    if reminder is None:
        return "Reminder was deleted before it was due."
    if reminder.dismissed_at is not None:
        return "Reminder was dismissed before it was due."
    if notification.dedupe_key != dedupe_key(reminder.id, reminder.remind_at):
        return "Reminder was moved to a different time."
    return None
