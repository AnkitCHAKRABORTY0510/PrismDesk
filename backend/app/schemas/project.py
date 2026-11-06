from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.admin import UserSummary

ProjectStatus = Literal["active", "archived", "deleted"]
MembershipRole = Literal["supervisor", "member", "guest"]


def _strip(value: str | None) -> str | None:
    return value.strip() if isinstance(value, str) else value


class ProjectCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=10000)
    objectives: str = Field(default="", max_length=10000)

    _strip_fields = field_validator("title", "description", "objectives")(_strip)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        if len(value) < 3:
            raise ValueError("Title must contain at least 3 characters.")
        return value


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    objectives: str | None = Field(default=None, max_length=10000)

    _strip_fields = field_validator("title", "description", "objectives")(_strip)


class ArchiveRequest(BaseModel):
    reason: str = Field(default="", max_length=500)


class MemberAddRequest(BaseModel):
    user_id: UUID
    membership_role: MembershipRole


class MemberRoleUpdate(BaseModel):
    membership_role: MembershipRole


class OwnershipTransferRequest(BaseModel):
    new_owner_id: UUID


class ProjectMemberResponse(BaseModel):
    id: UUID
    user: UserSummary
    membership_role: str
    membership_status: str
    joined_at: datetime
    removed_at: datetime | None = None


class ProjectPermissions(BaseModel):
    can_edit: bool
    can_contribute: bool
    can_manage_members: bool
    can_archive: bool
    can_unarchive: bool
    can_request_archive: bool
    can_delete: bool
    can_restore: bool
    can_review: bool


class ProjectResponse(BaseModel):
    id: UUID
    title: str
    description: str
    objectives: str
    status: str
    owner: UserSummary
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
    archive_requested_at: datetime | None = None
    archive_request_reason: str | None = None
    archived_at: datetime | None = None
    deleted_at: datetime | None = None
    purge_eligible_at: datetime | None = None
    member_count: int = 0
    supervisors: list[UserSummary] = []
    my_role: str | None = None
    permissions: ProjectPermissions
