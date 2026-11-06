from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.dependencies import require_role
from app.models.user import User

from app.schemas.admin import (
    PendingUserResponse,
    ApproveUserRequest,
    AdminActionResponse,
    UserManagementResponse,
)

from app.services.admin_service import (
    get_pending_users,
    get_all_users,
    approve_user,
    reject_user,
    suspend_user,
    reactivate_user,
)


router = APIRouter(
    prefix="/admin",
    tags=["Administrator"],
)


# List pending registrations.
@router.get(
    "/pending-users",
    response_model=list[PendingUserResponse],
)
def list_pending_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("Administrator")),
):
    return get_pending_users(db)


# Approve a registration and assign a role.
@router.post(
    "/users/{user_id}/approve",
    response_model=AdminActionResponse,
)
def approve_registration(
    user_id: UUID,
    request: ApproveUserRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("Administrator")),
):
    try:
        user = approve_user(
            db=db,
            user_id=user_id,
            role_name=request.role_name,
            admin_id=admin.id,
        )

        return AdminActionResponse(
            message="User approved successfully.",
            user_id=user.id,
            username=user.username,
            account_status=user.account_status,
            assigned_role=request.role_name,
        )

    except ValueError as error:
        detail = str(error)

        if detail == "User not found.":
            error_status = status.HTTP_404_NOT_FOUND
        elif detail.startswith("Only pending"):
            error_status = status.HTTP_409_CONFLICT
        else:
            error_status = status.HTTP_400_BAD_REQUEST

        raise HTTPException(
            status_code=error_status,
            detail=detail,
        )


# Reject a registration.
@router.post(
    "/users/{user_id}/reject",
    response_model=AdminActionResponse,
)
def reject_registration(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("Administrator")),
):
    try:
        user = reject_user(
            db=db,
            user_id=user_id,
        )

        return AdminActionResponse(
            message="User registration rejected.",
            user_id=user.id,
            username=user.username,
            account_status=user.account_status,
        )

    except ValueError as error:
        detail = str(error)

        if detail == "User not found.":
            error_status = status.HTTP_404_NOT_FOUND
        elif detail.startswith("Only pending"):
            error_status = status.HTTP_409_CONFLICT
        else:
            error_status = status.HTTP_400_BAD_REQUEST

        raise HTTPException(
            status_code=error_status,
            detail=detail,
        )
    
# List all registered users with optional filters.
@router.get(
    "/users",
    response_model=list[UserManagementResponse],
)
def list_all_users(
    search: str | None = Query(default=None, max_length=255),
    account_status: str | None = Query(default=None),
    role_name: str | None = Query(default=None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("Administrator")),
):
    allowed_statuses = {
        "pending",
        "approved",
        "rejected",
        "suspended",
    }

    allowed_roles = {
        "Administrator",
        "Professor",
        "Student",
        "Guest",
    }

    if account_status and account_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid account status filter.",
        )

    if role_name and role_name not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role filter.",
        )

    users = get_all_users(
        db=db,
        search=search,
        account_status=account_status,
        role_name=role_name,
    )

    return [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "account_status": user.account_status,
            "roles": [role.name for role in user.roles],
            "created_at": user.created_at,
        }
        for user in users
    ]

@router.patch(
    "/users/{user_id}/suspend",
    response_model=AdminActionResponse,
)
def suspend_registration(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("Administrator")),
):
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot suspend your own administrator account.",
        )

    try:
        user = suspend_user(
            db=db,
            user_id=user_id,
        )

        return AdminActionResponse(
            message="User account suspended successfully.",
            user_id=user.id,
            username=user.username,
            account_status=user.account_status,
        )

    except ValueError as error:
        detail = str(error)

        if detail == "User not found.":
            error_status = status.HTTP_404_NOT_FOUND
        else:
            error_status = status.HTTP_409_CONFLICT

        raise HTTPException(
            status_code=error_status,
            detail=detail,
        )

@router.patch(
    "/users/{user_id}/reactivate",
    response_model=AdminActionResponse,
)
def reactivate_registration(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("Administrator")),
):
    try:
        user = reactivate_user(
            db=db,
            user_id=user_id,
        )

        return AdminActionResponse(
            message="User account reactivated successfully.",
            user_id=user.id,
            username=user.username,
            account_status=user.account_status,
        )

    except ValueError as error:
        detail = str(error)

        if detail == "User not found.":
            error_status = status.HTTP_404_NOT_FOUND
        else:
            error_status = status.HTTP_409_CONFLICT

        raise HTTPException(
            status_code=error_status,
            detail=detail,
        )