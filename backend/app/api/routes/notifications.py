from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, page_params, require_capability
from app.core.config import settings
from app.core.errors import BadRequestError, ConflictError, NotFoundError, ServiceError
from app.core.rate_limit import rate_limit
from app.database.session import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.common import MessageResponse, Page, PageParams, paginate
from app.schemas.notification import (
    AnnouncementCreate,
    AnnouncementResponse,
    DiscordLinkStartResponse,
    DiscordStatusResponse,
    NotificationResponse,
    NotificationStatus,
    PreferenceItem,
    PreferencesUpdate,
)
from app.services import discord_link_service
from app.services.audit_service import record_audit
from app.services.notification_service import enqueue_notification, now_utc

router = APIRouter(prefix="/notifications", tags=["Notifications (Discord)"])


def _notification(n: Notification) -> NotificationResponse:
    return NotificationResponse.model_validate(n, from_attributes=True)


@router.get("/discord", response_model=DiscordStatusResponse)
def discord_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    account = discord_link_service.link_status(db, user)
    return DiscordStatusResponse(
        linked=account is not None,
        discord_username=account.discord_username if account else None,
        linked_at=account.linked_at if account else None,
        oauth_configured=settings.discord_oauth_configured,
        bot_configured=settings.discord_bot_configured,
    )


@router.post(
    "/discord/link",
    response_model=DiscordLinkStartResponse,
    dependencies=[Depends(rate_limit("discord_link", "LOGIN_RATE_LIMIT"))],
)
def start_discord_link(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return DiscordLinkStartResponse(authorize_url=discord_link_service.start_link(db, user))


@router.get("/discord/callback", include_in_schema=True)
def discord_callback(
    code: str | None = Query(default=None, max_length=200),
    state: str | None = Query(default=None, max_length=200),
    error: str | None = Query(default=None, max_length=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """OAuth2 redirect target. The one-time ``state`` binds it to the user."""

    target = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/settings/notifications"
    if error or not code or not state:
        return RedirectResponse(f"{target}?discord=cancelled", status_code=303)
    try:
        discord_link_service.complete_link(db, user, code, state)
    except ConflictError:
        return RedirectResponse(f"{target}?discord=conflict", status_code=303)
    except ServiceError:
        return RedirectResponse(f"{target}?discord=error", status_code=303)
    return RedirectResponse(f"{target}?discord=linked", status_code=303)


@router.post(
    "/discord/test",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit("discord_test", "LOGIN_RATE_LIMIT"))],
)
def send_test_message(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Queue a test DM to the current user's linked Discord account."""

    if discord_link_service.link_status(db, user) is None:
        raise BadRequestError("Link your Discord account first.")
    queued = enqueue_notification(
        db,
        recipient_id=user.id,
        category="administrative",
        event_type="discord.test",
        title="Prism Desk test message",
        body="If you can read this, Discord notifications from Prism Desk are working.",
        dedupe_key=f"discord.test:{user.id}:{now_utc().isoformat()}",
    )
    if not queued:
        raise BadRequestError("Turn on Administrative notifications to receive the test message.")
    db.commit()
    if not settings.discord_bot_configured:
        return MessageResponse(
            message="Test message queued, but the Discord bot token is not configured on the server yet."
        )
    return MessageResponse(message="Test message queued. It arrives as a Discord DM within a minute.")


@router.delete("/discord", response_model=MessageResponse)
def unlink_discord(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    discord_link_service.unlink(db, user)
    return MessageResponse(message="Discord account unlinked.")


@router.get("/preferences", response_model=list[PreferenceItem])
def get_preferences(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [
        PreferenceItem(category=category, enabled=enabled)
        for category, enabled in discord_link_service.get_preferences(db, user.id).items()
    ]


@router.put("/preferences", response_model=list[PreferenceItem])
def update_preferences(
    data: PreferencesUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    values = discord_link_service.set_preferences(
        db, user, {item.category: item.enabled for item in data.preferences}
    )
    return [PreferenceItem(category=category, enabled=enabled) for category, enabled in values.items()]


@router.get("/history", response_model=Page[NotificationResponse])
def my_notifications(
    status: NotificationStatus | None = None,
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    statement = (
        select(Notification).where(Notification.recipient_id == user.id).order_by(Notification.created_at.desc())
    )
    if status:
        statement = statement.where(Notification.status == status)
    items, total = paginate(db, statement, params)
    return Page(items=[_notification(n) for n in items], total=total, page=params.page, page_size=params.page_size)


@router.get("/queue", response_model=Page[NotificationResponse])
def notification_queue(
    status: NotificationStatus | None = None,
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: User = Depends(require_capability("announcements.send")),
):
    statement = select(Notification).order_by(Notification.created_at.desc())
    if status:
        statement = statement.where(Notification.status == status)
    items, total = paginate(db, statement, params)
    return Page(items=[_notification(n) for n in items], total=total, page=params.page, page_size=params.page_size)


@router.post("/{notification_id}/retry", response_model=NotificationResponse)
def retry_notification(
    notification_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_capability("announcements.send")),
):
    notification = db.get(Notification, notification_id)
    if not notification:
        raise NotFoundError("Notification not found.")
    if notification.status != "failed":
        raise ConflictError("Only failed notifications can be retried.")
    notification.status = "retry_scheduled"
    notification.next_attempt_at = now_utc()
    # Grant a fresh retry budget on top of the attempts already made.
    notification.max_attempts = notification.attempt_count + settings.NOTIFICATION_MAX_ATTEMPTS
    record_audit(db, admin.id, "notification.retried", "notification", notification.id)
    db.commit()
    db.refresh(notification)
    return _notification(notification)


@router.post("/announcements", response_model=AnnouncementResponse)
def send_announcement(
    data: AnnouncementCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_capability("announcements.send")),
):
    stamp = now_utc().isoformat()
    queued = 0
    channel = settings.DISCORD_ANNOUNCEMENT_CHANNEL_ID or None

    if data.post_to_channel and channel:
        queued += enqueue_notification(
            db,
            channel_id=channel,
            category="administrative",
            event_type="announcement",
            title=data.title,
            body=data.body,
            dedupe_key=f"announcement:channel:{stamp}",
        )

    if data.direct_message_all:
        recipients = db.scalars(select(User.id).where(User.account_status == "approved")).all()
        for recipient_id in recipients:
            queued += enqueue_notification(
                db,
                recipient_id=recipient_id,
                category="administrative",
                event_type="announcement",
                title=data.title,
                body=data.body,
                dedupe_key=f"announcement:{stamp}:{recipient_id}",
            )

    record_audit(
        db, admin.id, "announcement.sent", "announcement", None,
        {"title": data.title, "queued": queued, "channel": bool(data.post_to_channel and channel)},
    )
    db.commit()
    return AnnouncementResponse(queued=queued, channel_configured=bool(channel))
