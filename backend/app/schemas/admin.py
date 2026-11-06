from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

RoleName = Literal["Administrator", "Professor", "Student", "Guest"]
AccountStatus = Literal["pending", "approved", "rejected", "suspended"]


class PendingUserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    full_name: str
    account_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApproveUserRequest(BaseModel):
    role_name: Literal["Student", "Professor", "Guest"]


class RoleChangeRequest(BaseModel):
    role_name: RoleName


class AdminActionResponse(BaseModel):
    message: str
    user_id: UUID
    username: str
    account_status: str
    assigned_role: str | None = None
    roles: list[str] = []


class UserManagementResponse(BaseModel):
    id: UUID
    username: str
    email: str
    full_name: str
    account_status: str
    roles: list[str]
    created_at: datetime
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    suspended_at: datetime | None = None


class UserSummary(BaseModel):
    """Minimal public profile used in pickers and member lists."""

    id: UUID
    username: str
    full_name: str
    roles: list[str] = []


def user_management_response(user) -> UserManagementResponse:
    return UserManagementResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        account_status=user.account_status,
        roles=sorted(user.role_names),
        created_at=user.created_at,
        approved_at=user.approved_at,
        rejected_at=user.rejected_at,
        suspended_at=user.suspended_at,
    )


def user_summary(user) -> UserSummary:
    return UserSummary(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        roles=sorted(user.role_names),
    )
