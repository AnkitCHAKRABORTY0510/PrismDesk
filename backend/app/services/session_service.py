from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.user_session import UserSession
from app.core.config import settings
from app.core.session_security import (
    generate_session_token,
    hash_session_token,
)


def create_session(
    db: Session,
    user_id,
) -> tuple[str, UserSession]:

    now = datetime.now(timezone.utc)

    token = generate_session_token()
    token_hash = hash_session_token(token)

    session = UserSession(
        user_id=user_id,
        token_hash=token_hash,
        created_at=now,
        last_activity_at=now,
        expires_at=now + timedelta(
            hours=settings.SESSION_EXPIRE_HOURS
        ),
    )

    db.add(session)
    db.flush()

    return token, session


def get_active_session(
    db: Session,
    token: str,
) -> UserSession | None:

    token_hash = hash_session_token(token)

    session = db.execute(
        select(UserSession).where(
            UserSession.token_hash == token_hash,
            UserSession.revoked_at.is_(None),
        )
    ).scalar_one_or_none()

    if not session:
        return None

    now = datetime.now(timezone.utc)

    # Check absolute expiration.
    if session.expires_at <= now:
        session.revoked_at = now
        db.commit()
        return None

    # Check inactivity timeout.
    inactivity_limit = timedelta(
        minutes=settings.SESSION_INACTIVITY_MINUTES
    )

    if now - session.last_activity_at > inactivity_limit:
        session.revoked_at = now
        db.commit()
        return None

    # Update last activity at most once per minute to limit writes.
    if now - session.last_activity_at > timedelta(seconds=60):
        session.last_activity_at = now
        db.commit()

    return session


def revoke_session(
    db: Session,
    token: str,
) -> bool:

    token_hash = hash_session_token(token)

    session = db.execute(
        select(UserSession).where(
            UserSession.token_hash == token_hash,
            UserSession.revoked_at.is_(None),
        )
    ).scalar_one_or_none()

    if not session:
        return False

    session.revoked_at = datetime.now(timezone.utc)

    db.commit()

    return True


def revoke_all_user_sessions(db: Session, user_id: UUID) -> int:
    """Revoke every active session of a user (caller commits)."""

    result = db.execute(
        update(UserSession)
        .where(
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(timezone.utc))
    )

    return result.rowcount or 0
