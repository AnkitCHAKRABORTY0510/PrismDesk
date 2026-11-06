from fastapi import Depends, Cookie, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.config import settings
from app.models.user import User
from app.services.session_service import (
    get_active_session,
    revoke_session,
)


def get_current_user(
    token: str | None = Cookie(
        default=None,
        alias=settings.SESSION_COOKIE_NAME,
    ),
    db: Session = Depends(get_db),
) -> User:

    # Check whether the session cookie exists.
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    # Validate the session against the database.
    session = get_active_session(
        db=db,
        token=token,
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is invalid or expired.",
        )

    # Retrieve the authenticated user.
    user = session.user

    # Ensure the account is still approved.
    if user.account_status != "approved":
        revoke_session(
            db=db,
            token=token,
        )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not approved.",
        )

    return user

def require_role(required_role: str):
    def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:

        user_roles = [role.name for role in current_user.roles]

        if required_role not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

        return current_user

    return role_checker