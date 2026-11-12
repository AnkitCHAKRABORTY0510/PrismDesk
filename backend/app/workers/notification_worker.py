"""Background delivery of queued Discord notifications.

Run as a separate process next to the API:

    python -m app.workers.notification_worker

Rows are claimed with ``FOR UPDATE SKIP LOCKED`` so several workers can
run safely. Each attempt is recorded; transient failures are retried
with exponential backoff until ``max_attempts`` is reached.
"""

import logging
import signal
import time
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logging import configure_logging
from app.models.conference import Conference, ProjectConference
from app.models.notification import Notification, NotificationDeliveryAttempt
from app.models.research import ResearchPaper
from app.models.project import Project, ProjectMember
from app.models.task import Task, TaskAssignment
from app.services import discord_project_channels, handbook_reminder_dispatch
from app.services.discord_client import DeliveryResult, DiscordSender
from app.services.notification_service import (
    category_enabled,
    enqueue_notification,
    linked_account,
    now_utc,
    retry_delay,
)

logger = logging.getLogger("prism.notification_worker")

BATCH_SIZE = 20
STALE_PROCESSING = timedelta(minutes=10)


def _format(notification: Notification) -> str:
    return f"**{notification.title}**\n{notification.body}".strip()


# Channel posts that get a discussion thread. Only the lab-wide post's thread
# is stored on the paper ("Discuss on Discord"); project channels are private.
THREADED_EVENTS = {"paper.added": True, "paper.project_post": False}


def _open_paper_thread(db: Session, notification: Notification, sender: DiscordSender, message_id: str) -> None:
    """Start the discussion thread for a newly posted paper.

    A thread failure is logged but does not fail the delivered post.
    """

    store_on_paper = THREADED_EVENTS[notification.event_type]
    paper = db.get(ResearchPaper, notification.entity_id) if notification.entity_id else None
    if paper is None or (store_on_paper and paper.discord_thread_id):
        return

    thread = sender.start_thread(notification.channel_id, message_id, paper.title)
    if thread.success and thread.channel_id:
        if store_on_paper:
            paper.discord_thread_id = thread.channel_id
    else:
        logger.warning("Could not open a discussion thread for paper %s: %s", paper.id, thread.error)


def _deliver(db: Session, notification: Notification, sender: DiscordSender) -> DeliveryResult:
    if notification.channel_id:
        result = sender.send_message(notification.channel_id, _format(notification))
        if result.success and result.message_id and notification.event_type in THREADED_EVENTS:
            _open_paper_thread(db, notification, sender, result.message_id)
        return result

    # A handbook reminder may have been deleted, dismissed or moved since
    # it was queued; that is final, so do not retry it.
    cancelled = handbook_reminder_dispatch.cancel_reason(db, notification)
    if cancelled:
        return DeliveryResult(False, None, cancelled, retryable=False)

    # Re-check at send time: the user may have unlinked or opted out.
    account = linked_account(db, notification.recipient_id)
    if account is None:
        return DeliveryResult(False, None, "Recipient has no linked Discord account.", retryable=False)
    if not category_enabled(db, notification.recipient_id, notification.category):
        return DeliveryResult(False, None, "Recipient disabled this notification category.", retryable=False)

    if not account.dm_channel_id:
        opened = sender.open_dm_channel(account.discord_user_id)
        if not opened.success:
            return opened
        account.dm_channel_id = opened.channel_id

    return sender.send_message(account.dm_channel_id, _format(notification))


def recover_stale(db: Session, now: datetime) -> int:
    """Return rows stuck in 'processing' (e.g. a crashed worker) to the queue."""

    result = db.execute(
        update(Notification)
        .where(
            Notification.status == "processing",
            Notification.last_attempt_at < now - STALE_PROCESSING,
        )
        .values(status="retry_scheduled", next_attempt_at=now)
    )
    db.commit()
    return result.rowcount or 0


def claim_batch(db: Session, now: datetime) -> list[UUID]:
    ids = list(
        db.scalars(
            select(Notification.id)
            .where(
                Notification.status.in_(("pending", "retry_scheduled")),
                Notification.next_attempt_at <= now,
            )
            .order_by(Notification.next_attempt_at)
            .limit(BATCH_SIZE)
            .with_for_update(skip_locked=True)
        ).all()
    )
    if ids:
        db.execute(
            update(Notification)
            .where(Notification.id.in_(ids))
            .values(
                status="processing",
                attempt_count=Notification.attempt_count + 1,
                last_attempt_at=now,
            )
        )
    db.commit()
    return ids


def process_one(db: Session, notification_id: UUID, sender: DiscordSender, now: datetime) -> str:
    notification = db.get(Notification, notification_id)

    if not settings.discord_bot_configured:
        result = DeliveryResult(False, None, "Discord bot token is not configured.", retryable=True)
    else:
        try:
            result = _deliver(db, notification, sender)
        except Exception as error:  # network errors, timeouts, bad JSON
            result = DeliveryResult(False, None, f"{type(error).__name__} while contacting Discord.", True)

    db.add(
        NotificationDeliveryAttempt(
            notification_id=notification.id,
            attempt_number=notification.attempt_count,
            success=result.success,
            http_status=result.http_status,
            error=result.error,
        )
    )

    if result.success:
        notification.status = "sent"
        notification.sent_at = now
        notification.last_error = None
    elif result.retryable and notification.attempt_count < notification.max_attempts:
        notification.status = "retry_scheduled"
        notification.next_attempt_at = now + retry_delay(notification.attempt_count)
        notification.last_error = result.error
    else:
        notification.status = "failed"
        notification.last_error = result.error

    db.commit()

    log = logger.info if result.success else logger.warning
    log(
        "notification %s %s -> %s (attempt %s)",
        notification.id,
        notification.event_type,
        notification.status,
        notification.attempt_count,
    )
    return notification.status


def run_once(db: Session, sender: DiscordSender, now: datetime | None = None) -> dict[str, int]:
    now = now or now_utc()
    recover_stale(db, now)
    summary: dict[str, int] = {}
    for notification_id in claim_batch(db, now):
        status = process_one(db, notification_id, sender, now)
        summary[status] = summary.get(status, 0) + 1
    return summary


def schedule_reminders(db: Session, now: datetime | None = None) -> int:
    """Queue task-due and conference-deadline reminders (deduplicated)."""

    now = now or now_utc()
    queued = 0

    task_horizon = now + timedelta(hours=settings.TASK_REMINDER_HOURS)
    rows = db.execute(
        select(TaskAssignment, Task)
        .join(Task, Task.id == TaskAssignment.task_id)
        .outerjoin(Project, Project.id == Task.project_id)
        .where(
            TaskAssignment.status != "completed",
            Task.due_at.is_not(None),
            Task.due_at > now,
            Task.due_at <= task_horizon,
            (Task.project_id.is_(None)) | (Project.status == "active"),
        )
    ).all()
    for assignment, task in rows:
        queued += enqueue_notification(
            db,
            recipient_id=assignment.assignee_id,
            category="tasks",
            event_type="task.due_soon",
            title="Task deadline approaching",
            body=f"“{task.title}” is due {task.due_at:%Y-%m-%d %H:%M UTC}.",
            entity_type="task",
            entity_id=task.id,
            dedupe_key=f"task.due_soon:{assignment.id}:{task.due_at.isoformat()}",
        )

    conference_horizon = now + timedelta(days=settings.CONFERENCE_REMINDER_DAYS)
    rows = db.execute(
        select(Conference, ProjectMember.user_id)
        .join(ProjectConference, ProjectConference.conference_id == Conference.id)
        .join(Project, Project.id == ProjectConference.project_id)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(
            Conference.submission_deadline > now,
            Conference.submission_deadline <= conference_horizon,
            ProjectConference.status == "active",
            Project.status == "active",
            ProjectMember.membership_status == "active",
            ProjectMember.membership_role.in_(("owner", "supervisor", "member")),
        )
        .distinct()
    ).all()
    for conference, user_id in rows:
        queued += enqueue_notification(
            db,
            recipient_id=user_id,
            category="conferences",
            event_type="conference.deadline_approaching",
            title="Conference deadline approaching",
            body=f"{conference.name} submission deadline: {conference.submission_deadline:%Y-%m-%d %H:%M UTC}.",
            entity_type="conference",
            entity_id=conference.id,
            dedupe_key=f"conference.deadline:{conference.id}:{user_id}:{conference.submission_deadline.isoformat()}",
        )

    db.commit()
    return queued


def main() -> None:  # pragma: no cover - long-running process
    from app.database.session import engine

    configure_logging()
    factory = sessionmaker(bind=engine, autoflush=False)
    sender = DiscordSender()
    running = True

    def stop(*_):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    if not settings.discord_bot_configured:
        logger.warning("DISCORD_BOT_TOKEN is not set; notifications will be retried until it is configured.")

    last_reminder_scan = 0.0
    last_channel_sync = 0.0
    logger.info("Notification worker started.")
    while running:
        try:
            with factory() as db:
                if time.monotonic() - last_reminder_scan > 300:
                    schedule_reminders(db)
                    last_reminder_scan = time.monotonic()
                # Cheap (narrow time window) and run every poll so reminders
                # created a few minutes ahead are still queued before they are due.
                handbook_reminder_dispatch.dispatch_due_reminders(db)
                if time.monotonic() - last_channel_sync > 60:
                    discord_project_channels.sync_project_channels(db, sender)
                    last_channel_sync = time.monotonic()
                run_once(db, sender)
        except Exception:
            logger.exception("Notification worker iteration failed; continuing.")
        for _ in range(settings.NOTIFICATION_POLL_SECONDS):
            if not running:
                break
            time.sleep(1)
    logger.info("Notification worker stopped.")


if __name__ == "__main__":  # pragma: no cover
    main()
