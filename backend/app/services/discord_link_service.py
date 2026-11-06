import hashlib
import logging
import secrets
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.models.notification import (
    NOTIFICATION_CATEGORIES,
    DiscordAccount,
    DiscordOAuthState,
    NotificationPreference,
)
from app.models.user import User
from app.services import discord_client
from app.services.audit_service import record_audit
from app.services.notification_service import now_utc

logger = logging.getLogger("prism.discord")

STATE_TTL = timedelta(minutes=10)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def link_status(db: Session, user: User) -> DiscordAccount | None:
    return db.scalar(
        select(DiscordAccount).where(DiscordAccount.user_id == user.id, DiscordAccount.status == "linked")
    )


def start_link(db: Session, user: User) -> str:
    if not settings.discord_oauth_configured:
        raise BadRequestError("Discord linking is not configured on this server.")

    state = secrets.token_urlsafe(32)
    db.add(DiscordOAuthState(user_id=user.id, state_hash=_hash(state), expires_at=now_utc() + STATE_TTL))
    db.commit()
    return discord_client.oauth_authorize_url(state)


def complete_link(db: Session, user: User, code: str, state: str) -> DiscordAccount:
    stored = db.scalar(
        select(DiscordOAuthState).where(DiscordOAuthState.state_hash == _hash(state)).with_for_update()
    )
    if (
        not stored
        or stored.user_id != user.id
        or stored.used_at is not None
        or stored.expires_at < now_utc()
    ):
        raise BadRequestError("The Discord link request is invalid or has expired.")
    stored.used_at = now_utc()
    db.commit()

    try:
        identity = discord_client.oauth_fetch_identity(code)
    except Exception as error:
        logger.warning("Discord OAuth exchange failed: %s", type(error).__name__)
        raise BadRequestError("Discord did not confirm the account. Please try again.")

    discord_user_id = str(identity.get("id") or "")
    username = identity.get("global_name") or identity.get("username") or "Discord user"
    if not discord_user_id.isdigit():
        raise BadRequestError("Discord returned an unexpected account identifier.")

    account = db.scalar(select(DiscordAccount).where(DiscordAccount.user_id == user.id))
    if account is None:
        account = DiscordAccount(user_id=user.id, discord_user_id=discord_user_id, discord_username=username)
        db.add(account)
    else:
        if account.discord_user_id != discord_user_id:
            account.dm_channel_id = None
        account.discord_user_id = discord_user_id
        account.discord_username = username
        account.status = "linked"
        account.linked_at = now_utc()
        account.unlinked_at = None

    record_audit(db, user.id, "discord.linked", "user", user.id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("This Discord account is already linked to another Prism Desk user.")
    db.refresh(account)
    return account


def unlink(db: Session, user: User) -> None:
    account = link_status(db, user)
    if not account:
        raise NotFoundError("No Discord account is linked.")
    account.status = "unlinked"
    account.unlinked_at = now_utc()
    account.dm_channel_id = None
    record_audit(db, user.id, "discord.unlinked", "user", user.id)
    db.commit()


def get_preferences(db: Session, user_id: UUID) -> dict[str, bool]:
    stored = {
        p.category: p.enabled
        for p in db.scalars(select(NotificationPreference).where(NotificationPreference.user_id == user_id)).all()
    }
    return {category: stored.get(category, True) for category in NOTIFICATION_CATEGORIES}


def set_preferences(db: Session, user: User, values: dict[str, bool]) -> dict[str, bool]:
    for category, enabled in values.items():
        preference = db.get(NotificationPreference, (user.id, category))
        if preference is None:
            db.add(NotificationPreference(user_id=user.id, category=category, enabled=enabled))
        else:
            preference.enabled = enabled
    db.commit()
    return get_preferences(db, user.id)
