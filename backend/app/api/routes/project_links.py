from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.project_link import RepoLinkCreate, RepoLinkResponse
from app.services import project_link_service

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("/{project_id}/repo-links", response_model=list[RepoLinkResponse])
def list_repo_links(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return project_link_service.list_links(db, user, project_id)


@router.post(
    "/{project_id}/repo-links",
    response_model=RepoLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_repo_link(
    project_id: UUID,
    data: RepoLinkCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return project_link_service.add_link(db, user, project_id, data)


@router.delete("/{project_id}/repo-links/{link_id}", response_model=MessageResponse)
def remove_repo_link(
    project_id: UUID,
    link_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project_link_service.remove_link(db, user, project_id, link_id)
    return MessageResponse(message="Repository link removed.")
