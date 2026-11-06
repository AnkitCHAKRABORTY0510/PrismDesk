from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, page_params
from app.database.session import get_db
from app.models.user import User
from app.schemas.common import MessageResponse, Page, PageParams
from app.schemas.conference import (
    ConferenceCreate,
    ConferenceLinkRequest,
    ConferenceResponse,
    ConferenceUpdate,
)
from app.services import conference_service

router = APIRouter(prefix="/conferences", tags=["Conferences"])


def _one(db, user, conference) -> ConferenceResponse:
    return conference_service.conference_responses(db, user, [conference])[0]


@router.get("", response_model=Page[ConferenceResponse])
def list_conferences(
    search: str | None = Query(default=None, max_length=200),
    project_id: UUID | None = None,
    deadline_from: datetime | None = None,
    deadline_to: datetime | None = None,
    timing: Literal["upcoming", "overdue"] | None = None,
    include_archived_links: bool = False,
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conferences, total = conference_service.list_conferences(
        db, user, params, search, project_id, deadline_from, deadline_to, timing, include_archived_links
    )
    return Page(
        items=conference_service.conference_responses(db, user, conferences),
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post("", response_model=ConferenceResponse, status_code=status.HTTP_201_CREATED)
def create_conference(
    data: ConferenceCreate,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conference, linked_existing = conference_service.create_conference(db, user, data)
    result = _one(db, user, conference)
    result.linked_existing = linked_existing
    if linked_existing:
        response.status_code = status.HTTP_200_OK
    return result


@router.get("/{conference_id}", response_model=ConferenceResponse)
def get_conference(conference_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _one(db, user, conference_service.get_conference(db, user, conference_id))


@router.patch("/{conference_id}", response_model=ConferenceResponse)
def update_conference(
    conference_id: UUID,
    data: ConferenceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _one(db, user, conference_service.update_conference(db, user, conference_id, data))


@router.delete("/{conference_id}", response_model=MessageResponse)
def delete_conference(conference_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conference_service.delete_conference(db, user, conference_id)
    return MessageResponse(message="Conference deleted.")


@router.post("/{conference_id}/projects", response_model=ConferenceResponse)
def link_conference(
    conference_id: UUID,
    data: ConferenceLinkRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _one(db, user, conference_service.link_conference(db, user, conference_id, data.project_id))


@router.post("/{conference_id}/projects/{project_id}/archive", response_model=MessageResponse)
def archive_link(
    conference_id: UUID, project_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    conference_service.archive_link(db, user, conference_id, project_id)
    return MessageResponse(message="Conference association archived.")


@router.delete("/{conference_id}/projects/{project_id}", response_model=MessageResponse)
def unlink_conference(
    conference_id: UUID, project_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    conference_service.unlink_conference(db, user, conference_id, project_id)
    return MessageResponse(message="Conference removed from the project.")
