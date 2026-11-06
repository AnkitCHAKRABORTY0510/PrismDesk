from fastapi import Cookie, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.permissions import has_capability
from app.core.session_security import csrf_token_matches
from app.database.session import get_db
from app.models.user import User
from app.schemas.common import PageParams
from app.services.session_service import (
    get_active_session,
    revoke_session,
)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def get_current_user(
    request: Request,
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

    # Ensure the account is still approved. Suspension also revokes
    # sessions, this is a second line of defence.
    if user.account_status != "approved":
        revoke_session(
            db=db,
            token=token,
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your account is not approved.",
        )

    # Cookie-authenticated state changes must carry the CSRF token.
    if request.method not in SAFE_METHODS and not csrf_token_matches(
        token,
        request.headers.get(settings.CSRF_HEADER_NAME),
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing or invalid CSRF token.",
        )

    request.state.session_token = token

    return user


def require_role(*required_roles: str):
    """Allow the request when the user holds any of ``required_roles``."""

    def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:

        if not current_user.role_names.intersection(required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

        return current_user

    return role_checker


def require_capability(capability: str):
    def capability_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:

        if not has_capability(current_user.role_names, capability):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

        return current_user

    return capability_checker


def page_params(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PageParams:
    return PageParams(page=page, page_size=page_size)
