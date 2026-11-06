from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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


class AdminActionResponse(BaseModel):
    message: str
    user_id: UUID
    username: str
    account_status: str
    assigned_role: str | None = None

class UserManagementResponse(BaseModel):
    id: UUID
    username: str
    email: str
    full_name: str
    account_status: str
    roles: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
