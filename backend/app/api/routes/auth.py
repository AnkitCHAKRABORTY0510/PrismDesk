from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.permissions import capabilities_for
from app.core.rate_limit import rate_limit
from app.core.session_security import csrf_token_matches, derive_csrf_token
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
)
from app.services.auth_service import login_user, register_user
from app.services.session_service import get_active_session, revoke_session

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


def build_user_response(user: User, token: str, message: str) -> LoginResponse:
    roles = sorted(user.role_names)

    return LoginResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        roles=roles,
        capabilities=sorted(capabilities_for(roles)),
        csrf_token=derive_csrf_token(token),
        message=message,
    )


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("register", "REGISTER_RATE_LIMIT"))],
)
def register(
    user_data: RegisterRequest,
    db: Session = Depends(get_db),
):
    try:
        return register_user(db, user_data)

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        )


@router.post(
    "/login",
    response_model=LoginResponse,
    dependencies=[Depends(rate_limit("login", "LOGIN_RATE_LIMIT"))],
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

    # Set the server-managed session cookie.
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.SESSION_EXPIRE_HOURS * 60 * 60,
        path="/",
    )

    # Prevent browser caching of authentication responses.
    response.headers["Cache-Control"] = "no-store"

    return build_user_response(user, token, "Login successful.")


@router.get(
    "/me",
    response_model=LoginResponse,
)
def get_me(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "no-store"

    return build_user_response(
        user,
        request.state.session_token,
        "Authenticated user.",
    )


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    token: str | None = Cookie(
        default=None,
        alias=settings.SESSION_COOKIE_NAME,
    ),
    db: Session = Depends(get_db),
):
    # Prevent caching of the logout response.
    response.headers["Cache-Control"] = "no-store"

    # Revoke the server-side session if a cookie exists. A still-valid
    # session must present its CSRF token so other sites cannot log the
    # user out; an expired session is simply cleared.
    if token:
        active = get_active_session(db=db, token=token)

        if active and not csrf_token_matches(
            token,
            request.headers.get(settings.CSRF_HEADER_NAME),
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing or invalid CSRF token.",
            )

        revoke_session(
            db=db,
            token=token,
        )

    # Clear the browser's session cookie.
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )

    return {
        "message": "Logout successful."
    }
