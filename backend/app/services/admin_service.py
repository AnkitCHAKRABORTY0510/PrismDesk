from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.user import User
from app.models.role import Role
from app.models.user_session import UserSession

ALLOWED_ROLES = {"Student", "Professor", "Guest"}


def get_pending_users(db: Session) -> list[User]:
    """Retrieve all users awaiting administrator approval."""

    statement = (
        select(User)
        .where(User.account_status == "pending")
        .order_by(User.created_at.asc())
    )

    return list(db.scalars(statement).all())


def approve_user(
    db: Session,
    user_id: UUID,
    role_name: str,
    admin_id: UUID,
) -> User:
    """Approve a pending user and assign an application role."""

    if role_name not in ALLOWED_ROLES:
        raise ValueError("Invalid role assignment.")

    try:
        # Lock the user row to prevent concurrent approval.
        user = db.execute(
            select(User)
            .where(User.id == user_id)
            .with_for_update()
        ).scalar_one_or_none()

        if not user:
            raise ValueError("User not found.")

        if user.account_status != "pending":
            raise ValueError("Only pending accounts can be approved.")

        # Retrieve the selected role.
        role = db.execute(
            select(Role).where(Role.name == role_name)
        ).scalar_one_or_none()

        if not role:
            raise ValueError("Selected role does not exist.")

        # Assign the role and approve the account.
        user.roles.append(role)
        user.account_status = "approved"
        user.approved_by = admin_id
        user.approved_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(user)

        return user

    except Exception:
        db.rollback()
        raise


def reject_user(
    db: Session,
    user_id: UUID,
) -> User:
    """Reject a pending registration."""

    try:
        user = db.execute(
            select(User)
            .where(User.id == user_id)
            .with_for_update()
        ).scalar_one_or_none()

        if not user:
            raise ValueError("User not found.")

        if user.account_status != "pending":
            raise ValueError("Only pending accounts can be rejected.")

        user.account_status = "rejected"

        db.commit()
        db.refresh(user)

        return user

    except Exception:
        db.rollback()
        raise

def get_all_users(
    db: Session,
    search: str | None = None,
    account_status: str | None = None,
    role_name: str | None = None,
) -> list[User]:
    """Retrieve users with optional search and filters."""

    statement = select(User).order_by(User.created_at.desc())

    # Search by username, email or full name.
    if search:
        search_term = f"%{search.strip()}%"

        statement = statement.where(
            or_(
                User.username.ilike(search_term),
                User.email.ilike(search_term),
                User.full_name.ilike(search_term),
            )
        )

    # Filter by account status.
    if account_status:
        statement = statement.where(
            User.account_status == account_status
        )

    # Filter by assigned role.
    if role_name:
        statement = statement.where(
            User.roles.any(Role.name == role_name)
        )

    return list(db.scalars(statement).unique().all())
def suspend_user(
    db: Session,
    user_id: UUID,
) -> User:
    """Suspend an approved account and revoke its active sessions."""

    try:
        user = db.execute(
            select(User)
            .where(User.id == user_id)
            .with_for_update()
        ).scalar_one_or_none()

        if not user:
            raise ValueError("User not found.")

        if user.account_status != "approved":
            raise ValueError("Only approved accounts can be suspended.")

        user.account_status = "suspended"

        # Revoke all active sessions belonging to this user.
        active_sessions = db.scalars(
            select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
            )
        ).all()

        now = datetime.now(timezone.utc)

        for session in active_sessions:
            session.revoked_at = now

        db.commit()
        db.refresh(user)

        return user

    except Exception:
        db.rollback()
        raise
def reactivate_user(
    db: Session,
    user_id: UUID,
) -> User:
    """Reactivate a suspended account."""

    try:
        user = db.execute(
            select(User)
            .where(User.id == user_id)
            .with_for_update()
        ).scalar_one_or_none()

        if not user:
            raise ValueError("User not found.")

        if user.account_status != "suspended":
            raise ValueError(
                "Only suspended accounts can be reactivated."
            )

        user.account_status = "approved"

        db.commit()
        db.refresh(user)

        return user

    except Exception:
        db.rollback()
        raise