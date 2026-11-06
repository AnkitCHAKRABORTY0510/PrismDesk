from fastapi import (APIRouter, Depends, HTTPException, status, Response, Cookie,)
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.core.config import settings
from app.schemas.auth import (RegisterRequest, RegisterResponse, LoginRequest, LoginResponse,)
from app.api.dependencies import get_current_user
from app.services.auth_service import (
    register_user,
    login_user,
)

from app.services.session_service import (
    get_active_session,
    revoke_session,
)
from app.models.user import User

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_data: RegisterRequest,
    db: Session = Depends(get_db),
):

    try:
        new_user = register_user(db, user_data)

        return new_user

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        )

@router.post(
    "/login",
    response_model=LoginResponse,
    tags=["Authentication"],
)

def login(
    user_data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    try:
        user, token = login_user(
            db=db,
            identifier=user_data.identifier,
            password=user_data.password,
        )

        # Set the server-managed session cookie.
        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=token,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite="lax",
            max_age=settings.SESSION_EXPIRE_HOURS * 60 * 60,
            path="/",
        )

        # Prevent browser caching of authentication responses.
        response.headers["Cache-Control"] = "no-store"

        return LoginResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            roles=[role.name for role in user.roles],
            message="Login successful.",
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        )

    except PermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        )

@router.get(
    "/me",
    response_model=LoginResponse,
)
def get_me(
    response: Response,
    user: User = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "no-store"

    return LoginResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        roles=[role.name for role in user.roles],
        message="Authenticated user.",
    )

@router.post(
    "/logout",
    tags=["Authentication"],
)
def logout(
    response: Response,
    token: str | None = Cookie(
        default=None,
        alias=settings.SESSION_COOKIE_NAME,
    ),
    db: Session = Depends(get_db),
):
    # Prevent caching of the logout response.
    response.headers["Cache-Control"] = "no-store"

    # Revoke the server-side session if a cookie exists.
    if token:
        revoke_session(
            db=db,
            token=token,
        )

    # Clear the browser's session cookie.
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
    )

    return {
        "message": "Logout successful."
    }