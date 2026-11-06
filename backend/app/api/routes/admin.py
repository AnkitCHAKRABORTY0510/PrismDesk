from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import page_params, require_role
from app.core.permissions import ADMINISTRATOR
from app.database.session import get_db
from app.models.user import User
from app.schemas.admin import (
    AccountStatus,
    AdminActionResponse,
    ApproveUserRequest,
    PendingUserResponse,
    RoleChangeRequest,
    RoleName,
    UserManagementResponse,
    user_management_response,
)
from app.schemas.common import Page, PageParams
from app.services import admin_service

router = APIRouter(
    prefix="/admin",
    tags=["Administrator"],
)

require_admin = require_role(ADMINISTRATOR)


def _action(message: str, user: User, assigned_role: str | None = None):
    return AdminActionResponse(
        message=message,
        user_id=user.id,
        username=user.username,
        account_status=user.account_status,
        assigned_role=assigned_role,
        roles=sorted(user.role_names),
    )


# List pending registrations.
@router.get(
    "/pending-users",
    response_model=list[PendingUserResponse],
)
def list_pending_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return admin_service.get_pending_users(db)


# Approve a registration and assign a role.
@router.post(
    "/users/{user_id}/approve",
    response_model=AdminActionResponse,
)
def approve_registration(
    user_id: UUID,
    request: ApproveUserRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = admin_service.approve_user(db, user_id, request.role_name, admin)
    return _action("User approved successfully.", user, request.role_name)


# Reject a registration.
@router.post(
    "/users/{user_id}/reject",
    response_model=AdminActionResponse,
)
def reject_registration(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = admin_service.reject_user(db, user_id, admin)
    return _action("User registration rejected.", user)


# List all registered users with optional filters.
@router.get(
    "/users",
    response_model=Page[UserManagementResponse],
)
def list_all_users(
    search: str | None = Query(default=None, max_length=255),
    account_status: AccountStatus | None = Query(default=None),
    role_name: RoleName | None = Query(default=None),
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    users, total = admin_service.get_all_users(
        db=db,
        params=params,
        search=search,
        account_status=account_status,
        role_name=role_name,
    )

    return Page(
        items=[user_management_response(user) for user in users],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get(
    "/users/{user_id}",
    response_model=UserManagementResponse,
)
def get_user_detail(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return user_management_response(admin_service.get_user(db, user_id))


@router.patch(
    "/users/{user_id}/suspend",
    response_model=AdminActionResponse,
)
def suspend_registration(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = admin_service.suspend_user(db, user_id, admin)
    return _action("User account suspended successfully.", user)


@router.patch(
    "/users/{user_id}/reactivate",
    response_model=AdminActionResponse,
)
def reactivate_registration(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = admin_service.reactivate_user(db, user_id, admin)
    return _action("User account reactivated successfully.", user)


@router.post(
    "/users/{user_id}/roles",
    response_model=AdminActionResponse,
)
def assign_user_role(
    user_id: UUID,
    request: RoleChangeRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = admin_service.assign_role(db, user_id, request.role_name, admin)
    return _action("Role assigned.", user, request.role_name)


@router.delete(
    "/users/{user_id}/roles/{role_name}",
    response_model=AdminActionResponse,
)
def remove_user_role(
    user_id: UUID,
    role_name: RoleName,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = admin_service.remove_role(db, user_id, role_name, admin)
    return _action("Role removed.", user)
