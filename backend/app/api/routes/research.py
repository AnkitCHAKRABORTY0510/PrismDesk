from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, page_params
from app.database.session import get_db
from app.models.user import User
from app.schemas.common import MessageResponse, Page, PageParams
from app.schemas.research import (
    NoteCreate,
    NoteResponse,
    NoteUpdate,
    PaperCreate,
    PaperResponse,
    PaperUpdate,
    ProjectLinkRequest,
    ReadingProgressResponse,
    ReadingProgressUpdate,
    ReadingStatus,
)
from app.services import research_service

router = APIRouter(prefix="/research", tags=["Research Library"])


def _one(db, user, paper) -> PaperResponse:
    return research_service.paper_responses(db, user, [paper])[0]


def _note(note) -> NoteResponse:
    return NoteResponse(
        id=note.id,
        paper_id=note.paper_id,
        project_id=note.project_id,
        content=note.content,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.get("/papers", response_model=Page[PaperResponse])
def list_papers(
    search: str | None = Query(default=None, max_length=200),
    author: str | None = Query(default=None, max_length=200),
    keyword: str | None = Query(default=None, max_length=100),
    year: int | None = Query(default=None, ge=1800, le=2200),
    year_from: int | None = Query(default=None, ge=1800, le=2200),
    year_to: int | None = Query(default=None, ge=1800, le=2200),
    project_id: UUID | None = None,
    reading_status: ReadingStatus | None = None,
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    papers, total = research_service.list_papers(
        db, user, params, search, author, keyword, year, year_from, year_to, project_id, reading_status
    )
    return Page(
        items=research_service.paper_responses(db, user, papers),
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post("/papers", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
def create_paper(
    data: PaperCreate,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    paper, linked_existing = research_service.create_paper(db, user, data)
    result = _one(db, user, paper)
    result.linked_existing = linked_existing
    if linked_existing:
        response.status_code = status.HTTP_200_OK
    return result


@router.get("/papers/{paper_id}", response_model=PaperResponse)
def get_paper(
    paper_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _one(db, user, research_service.get_paper(db, user, paper_id))


@router.patch("/papers/{paper_id}", response_model=PaperResponse)
def update_paper(
    paper_id: UUID,
    data: PaperUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _one(db, user, research_service.update_paper(db, user, paper_id, data))


@router.post("/papers/{paper_id}/projects", response_model=PaperResponse)
def link_paper(
    paper_id: UUID,
    data: ProjectLinkRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _one(db, user, research_service.link_paper(db, user, paper_id, data.project_id))


@router.delete("/papers/{paper_id}/projects/{project_id}", response_model=MessageResponse)
def unlink_paper(
    paper_id: UUID,
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    research_service.unlink_paper(db, user, paper_id, project_id)
    return MessageResponse(message="Paper removed from the project.")


@router.put("/papers/{paper_id}/progress", response_model=ReadingProgressResponse)
def set_progress(
    paper_id: UUID,
    data: ReadingProgressUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    progress = research_service.set_reading_status(db, user, paper_id, data.status, data.project_id)
    return ReadingProgressResponse(
        paper_id=progress.paper_id,
        project_id=progress.project_id,
        user_id=progress.user_id,
        status=progress.status,
        updated_at=progress.updated_at,
    )


@router.get("/progress/me", response_model=list[ReadingProgressResponse])
def my_progress(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return [
        ReadingProgressResponse(
            paper_id=progress.paper_id,
            paper_title=title,
            project_id=progress.project_id,
            user_id=progress.user_id,
            status=progress.status,
            updated_at=progress.updated_at,
        )
        for progress, title in research_service.my_reading_progress(db, user)
    ]


@router.get("/projects/{project_id}/progress", response_model=list[ReadingProgressResponse])
def project_progress(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return [
        ReadingProgressResponse(
            paper_id=progress.paper_id,
            paper_title=title,
            project_id=progress.project_id,
            user_id=progress.user_id,
            username=username,
            status=progress.status,
            updated_at=progress.updated_at,
        )
        for progress, title, username in research_service.project_reading_progress(db, user, project_id)
    ]


@router.get("/papers/{paper_id}/notes", response_model=list[NoteResponse])
def list_notes(
    paper_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return [_note(note) for note in research_service.list_notes(db, user, paper_id)]


@router.post("/papers/{paper_id}/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(
    paper_id: UUID,
    data: NoteCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _note(research_service.create_note(db, user, paper_id, data.content, data.project_id))


@router.patch("/notes/{note_id}", response_model=NoteResponse)
def update_note(
    note_id: UUID,
    data: NoteUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _note(research_service.update_note(db, user, note_id, data.content))


@router.delete("/notes/{note_id}", response_model=MessageResponse)
def delete_note(
    note_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    research_service.delete_note(db, user, note_id)
    return MessageResponse(message="Note deleted.")
