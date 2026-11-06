from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, needs_rehash, verify_password
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.services.session_service import create_session

# Verified against when the account does not exist, so a failed login
# costs the same time whether or not the username is registered.
_DUMMY_HASH = hash_password("prism-desk-timing-equalizer")


def register_user(
    db: Session,
    user_data: RegisterRequest,
) -> User:
    # Public registration never assigns roles; an administrator assigns
    # them during approval.
    new_user = User(
        username=user_data.username,
        email=str(user_data.email),
        full_name=user_data.full_name,
        password_hash=hash_password(user_data.password),
        account_status="pending",
    )

    db.add(new_user)

    try:
        db.commit()
        db.refresh(new_user)

    except IntegrityError:
        db.rollback()
        raise ValueError(
            "Username or email is already registered."
        )

    return new_user


def login_user(
    db: Session,
    identifier: str,
    password: str,
):
    # Find user by username or email.
    user = db.execute(
        select(User).where(
            or_(
                func.lower(User.username) == identifier.lower(),
                func.lower(User.email) == identifier.lower(),
            )
        )
    ).scalar_one_or_none()

    if not user:
        verify_password(password, _DUMMY_HASH)
        raise ValueError("Invalid username/email or password.")

    # Reject invalid credentials.
    if not verify_password(password, user.password_hash):
        raise ValueError("Invalid username/email or password.")

    # Only approved accounts can log in.
    if user.account_status != "approved":
        raise PermissionError(
            "Your account is not approved for login."
        )

    # Upgrade the stored hash when Argon2 parameters change.
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)

    # Create a server-managed session.
    token, session = create_session(
        db=db,
        user_id=user.id,
    )

    db.commit()

    return user, token
