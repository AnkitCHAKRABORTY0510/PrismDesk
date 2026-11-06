from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.core.permissions import ADMINISTRATOR, ALL_ROLES, APPROVAL_ROLES
from app.models.role import Role
from app.models.user import User
from app.schemas.common import PageParams, paginate
from app.services.audit_service import record_audit
from app.services.session_service import revoke_all_user_sessions

ALLOWED_ROLES = set(APPROVAL_ROLES)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _lock_user(db: Session, user_id: UUID) -> User:
    user = db.execute(
        select(User).where(User.id == user_id).with_for_update()
    ).scalar_one_or_none()

    if not user:
        raise NotFoundError("User not found.")

    return user


def _get_role(db: Session, role_name: str) -> Role:
    if role_name not in ALL_ROLES:
        raise BadRequestError("Invalid role.")

    role = db.execute(
        select(Role).where(Role.name == role_name)
    ).scalar_one_or_none()

    if not role:
        raise BadRequestError("Selected role does not exist.")

    return role


def _active_admin_count(db: Session) -> int:
    return db.scalar(
        select(func.count(func.distinct(User.id)))
        .join(User.roles)
        .where(
            Role.name == ADMINISTRATOR,
            User.account_status == "approved",
        )
    ) or 0


def get_pending_users(db: Session) -> list[User]:
    """Retrieve all users awaiting administrator approval."""

    statement = (
        select(User)
        .where(User.account_status == "pending")
        .order_by(User.created_at.asc())
    )

    return list(db.scalars(statement).all())


def get_user(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)

    if not user:
        raise NotFoundError("User not found.")

    return user


def approve_user(
    db: Session,
    user_id: UUID,
    role_name: str,
    admin: User,
) -> User:
    """Approve a pending user and assign a non-administrative role."""

    if role_name not in ALLOWED_ROLES:
        raise BadRequestError("Invalid role assignment.")

    if user_id == admin.id:
        raise ForbiddenError("You cannot approve your own registration.")

    try:
        user = _lock_user(db, user_id)

        if user.account_status != "pending":
            raise ConflictError("Only pending accounts can be approved.")

        role = _get_role(db, role_name)

        if role not in user.roles:
            user.roles.append(role)

        user.account_status = "approved"
        user.approved_by = admin.id
        user.approved_at = _now()

        record_audit(
            db, admin.id, "user.approved", "user", user.id,
            {"role": role_name, "username": user.username},
        )

        from app.services.notification_service import enqueue_notification

        enqueue_notification(
            db,
            recipient_id=user.id,
            category="administrative",
            event_type="account.approved",
            title="Prism Desk account approved",
            body=f"Your account was approved with the {role_name} role.",
            dedupe_key=f"account.approved:{user.id}",
        )

        db.commit()
        db.refresh(user)

        return user

    except Exception:
        db.rollback()
        raise


def reject_user(
    db: Session,
    user_id: UUID,
    admin: User,
) -> User:
    """Reject a pending registration."""

    if user_id == admin.id:
        raise ForbiddenError("You cannot reject your own account.")

    try:
        user = _lock_user(db, user_id)

        if user.account_status != "pending":
            raise ConflictError("Only pending accounts can be rejected.")

        user.account_status = "rejected"
        user.rejected_by = admin.id
        user.rejected_at = _now()

        record_audit(
            db, admin.id, "user.rejected", "user", user.id,
            {"username": user.username},
        )

        db.commit()
        db.refresh(user)

        return user

    except Exception:
        db.rollback()
        raise


def get_all_users(
    db: Session,
    params: PageParams,
    search: str | None = None,
    account_status: str | None = None,
    role_name: str | None = None,
) -> tuple[list[User], int]:
    """Retrieve users with optional search and filters."""

    statement = select(User).order_by(User.created_at.desc())

    # Search by username, email or full name. Values are bound
    # parameters, so user input never becomes SQL.
    if search and search.strip():
        search_term = f"%{search.strip()}%"

        statement = statement.where(
            or_(
                User.username.ilike(search_term),
                User.email.ilike(search_term),
                User.full_name.ilike(search_term),
            )
        )

    if account_status:
        statement = statement.where(User.account_status == account_status)

    if role_name:
        statement = statement.where(User.roles.any(Role.name == role_name))

    return paginate(db, statement, params)


def suspend_user(
    db: Session,
    user_id: UUID,
    admin: User,
) -> User:
    """Suspend an approved account and revoke its active sessions."""

    if user_id == admin.id:
        raise BadRequestError(
            "You cannot suspend your own administrator account."
        )

    try:
        user = _lock_user(db, user_id)

        if user.account_status != "approved":
            raise ConflictError("Only approved accounts can be suspended.")

        if ADMINISTRATOR in user.role_names and _active_admin_count(db) <= 1:
            raise ConflictError("The last active administrator cannot be suspended.")

        user.account_status = "suspended"
        user.suspended_by = admin.id
        user.suspended_at = _now()

        revoked = revoke_all_user_sessions(db, user.id)

        record_audit(
            db, admin.id, "user.suspended", "user", user.id,
            {"username": user.username, "sessions_revoked": revoked},
        )

        db.commit()
        db.refresh(user)

        return user

    except Exception:
        db.rollback()
        raise


def reactivate_user(
    db: Session,
    user_id: UUID,
    admin: User,
) -> User:
    """Reactivate a suspended account. The user must log in again."""

    try:
        user = _lock_user(db, user_id)

        if user.account_status != "suspended":
            raise ConflictError(
                "Only suspended accounts can be reactivated."
            )

        user.account_status = "approved"
        user.suspended_by = None
        user.suspended_at = None

        # Any session that somehow survived suspension is invalidated so
        # a fresh login is required.
        revoke_all_user_sessions(db, user.id)

        record_audit(
            db, admin.id, "user.reactivated", "user", user.id,
            {"username": user.username},
        )

        db.commit()
        db.refresh(user)

        return user

    except Exception:
        db.rollback()
        raise


def assign_role(
    db: Session,
    user_id: UUID,
    role_name: str,
    admin: User,
) -> User:
    try:
        user = _lock_user(db, user_id)

        if user.account_status not in ("approved", "suspended"):
            raise ConflictError(
                "Roles can only be changed for approved or suspended accounts."
            )

        role = _get_role(db, role_name)

        if role in user.roles:
            raise ConflictError("The user already has this role.")

        user.roles.append(role)

        record_audit(
            db, admin.id, "user.role_assigned", "user", user.id,
            {"role": role_name, "username": user.username},
        )

        db.commit()
        db.refresh(user)

        return user

    except Exception:
        db.rollback()
        raise


def remove_role(
    db: Session,
    user_id: UUID,
    role_name: str,
    admin: User,
) -> User:
    try:
        user = _lock_user(db, user_id)
        role = _get_role(db, role_name)

        if role not in user.roles:
            raise ConflictError("The user does not have this role.")

        if len(user.roles) <= 1:
            raise ConflictError("A user must keep at least one role.")

        if role_name == ADMINISTRATOR:
            if user.id == admin.id:
                raise ForbiddenError(
                    "You cannot remove your own Administrator role."
                )

            if (
                user.account_status == "approved"
                and _active_admin_count(db) <= 1
            ):
                raise ConflictError(
                    "The last active administrator cannot lose the role."
                )

        user.roles.remove(role)

        record_audit(
            db, admin.id, "user.role_removed", "user", user.id,
            {"role": role_name, "username": user.username},
        )

        db.commit()
        db.refresh(user)

        return user

    except Exception:
        db.rollback()
        raise
