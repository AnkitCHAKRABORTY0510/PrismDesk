from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, page_params
from app.database.session import get_db
from app.models.user import User
from app.schemas.admin import user_summary
from app.schemas.common import MessageResponse, Page, PageParams
from app.schemas.project import (
    ArchiveRequest,
    MemberAddRequest,
    MemberRoleUpdate,
    OwnershipTransferRequest,
    ProjectCreate,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectStatus,
    ProjectUpdate,
)
from app.services import project_service
from app.services.project_access import get_project_access

router = APIRouter(prefix="/projects", tags=["Projects"])


def _member_response(member) -> ProjectMemberResponse:
    return ProjectMemberResponse(
        id=member.id,
        user=user_summary(member.user),
        membership_role=member.membership_role,
        membership_status=member.membership_status,
        joined_at=member.joined_at,
        removed_at=member.removed_at,
    )


@router.get("", response_model=Page[ProjectResponse])
def list_projects(
    status_filter: ProjectStatus | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=200),
    mine: bool = False,
    user_id: UUID | None = None,
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    projects, total = project_service.list_projects(
        db, user, params, status_filter, search, mine, user_id
    )
    accesses = project_service.build_accesses(db, user, projects)
    return Page(
        items=project_service.summary_responses(db, accesses),
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    access = project_service.create_project(db, user, data)
    return project_service.project_response(db, access)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return project_service.project_response(db, get_project_access(db, user, project_id))


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    access = project_service.update_project(db, user, project_id, data)
    return project_service.project_response(db, access)


@router.post("/{project_id}/archive-request", response_model=ProjectResponse)
def request_archive(
    project_id: UUID,
    data: ArchiveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    access = project_service.request_archive(db, user, project_id, data.reason)
    return project_service.project_response(db, access)


@router.post("/{project_id}/archive", response_model=ProjectResponse)
def archive_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    access = project_service.archive_project(db, user, project_id)
    return project_service.project_response(db, access)


@router.post("/{project_id}/unarchive", response_model=ProjectResponse)
def unarchive_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    access = project_service.unarchive_project(db, user, project_id)
    return project_service.project_response(db, access)


@router.delete("/{project_id}", response_model=ProjectResponse)
def soft_delete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    access = project_service.soft_delete_project(db, user, project_id)
    return project_service.project_response(db, access)


@router.post("/{project_id}/restore", response_model=ProjectResponse)
def restore_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    access = project_service.restore_project(db, user, project_id)
    return project_service.project_response(db, access)


@router.delete("/{project_id}/permanent", response_model=MessageResponse)
def purge_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project_service.purge_project(db, user, project_id)
    return MessageResponse(message="Project permanently deleted.")


@router.post("/{project_id}/transfer-ownership", response_model=ProjectResponse)
def transfer_ownership(
    project_id: UUID,
    data: OwnershipTransferRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    access = project_service.transfer_ownership(db, user, project_id, data.new_owner_id)
    return project_service.project_response(db, access)


@router.get("/{project_id}/members", response_model=list[ProjectMemberResponse])
def list_members(
    project_id: UUID,
    include_removed: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    members = project_service.list_members(db, user, project_id, include_removed)
    return [_member_response(member) for member in members]


@router.post(
    "/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    project_id: UUID,
    data: MemberAddRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    member = project_service.add_member(db, user, project_id, data.user_id, data.membership_role)
    return _member_response(member)


@router.patch("/{project_id}/members/{member_user_id}", response_model=ProjectMemberResponse)
def change_member_role(
    project_id: UUID,
    member_user_id: UUID,
    data: MemberRoleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    member = project_service.change_member_role(
        db, user, project_id, member_user_id, data.membership_role
    )
    return _member_response(member)


@router.delete("/{project_id}/members/{member_user_id}", response_model=MessageResponse)
def remove_member(
    project_id: UUID,
    member_user_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project_service.remove_member(db, user, project_id, member_user_id)
    return MessageResponse(message="Member removed.")
