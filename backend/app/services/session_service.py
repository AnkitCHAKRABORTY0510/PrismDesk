from datetime import datetime, timedelta, timezone

from sqlalchemy import select
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

    # Update last activity.
    session.last_activity_at = now
    db.commit()
    db.refresh(session)

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
