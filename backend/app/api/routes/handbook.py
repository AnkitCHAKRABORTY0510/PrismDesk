from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, page_params
from app.database.session import get_db
from app.models.user import User
from app.schemas.common import Page, PageParams
from app.schemas.handbook import (
    CommentCreate,
    EntryCreate,
    EntryResponse,
    EntryUpdate,
    ProgressDay,
    SummaryCreate,
    SummaryResponse,
    SummaryUpdate,
    VersionResponse,
)
from app.services import handbook_service

router = APIRouter(prefix="/handbook", tags=["Research Handbook"])


def _entry(db, user, entry) -> EntryResponse:
    return handbook_service.entry_responses(db, user, [entry], with_comments=True)[0]


def _summary(summary) -> SummaryResponse:
    return SummaryResponse.model_validate(summary, from_attributes=True)


@router.get("/entries", response_model=Page[EntryResponse])
def list_entries(
    project_id: UUID | None = None,
    student_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    entries, total = handbook_service.list_entries(db, user, params, project_id, student_id, date_from, date_to)
    return Page(
        items=handbook_service.entry_responses(db, user, entries),
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post("/entries", response_model=EntryResponse, status_code=status.HTTP_201_CREATED)
def create_entry(data: EntryCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _entry(db, user, handbook_service.create_entry(db, user, data))


@router.get("/entries/{entry_id}", response_model=EntryResponse)
def get_entry(entry_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    entry, _ = handbook_service.get_entry(db, user, entry_id)
    return _entry(db, user, entry)


@router.patch("/entries/{entry_id}", response_model=EntryResponse)
def update_entry(
    entry_id: UUID, data: EntryUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return _entry(db, user, handbook_service.update_entry(db, user, entry_id, data))


@router.get("/entries/{entry_id}/versions", response_model=list[VersionResponse])
def entry_versions(entry_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [
        VersionResponse(version=v.version, snapshot=v.snapshot, edited_at=v.edited_at)
        for v in handbook_service.entry_versions(db, user, entry_id)
    ]


@router.post("/entries/{entry_id}/comments", response_model=EntryResponse, status_code=status.HTTP_201_CREATED)
def add_comment(
    entry_id: UUID, data: CommentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    handbook_service.add_comment(db, user, entry_id, data.body, data.parent_id)
    entry, _ = handbook_service.get_entry(db, user, entry_id)
    return _entry(db, user, entry)


@router.get("/progress", response_model=list[ProgressDay])
def progress(
    project_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    date_to = date_to or date.today()
    date_from = date_from or date_to - timedelta(days=30)
    return [
        ProgressDay(entry_date=day, entry_count=entries, student_count=students)
        for day, entries, students in handbook_service.progress_by_date(db, user, project_id, date_from, date_to)
    ]


@router.get("/summaries", response_model=Page[SummaryResponse])
def list_summaries(
    date_from: date | None = None,
    date_to: date | None = None,
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    summaries, total = handbook_service.list_summaries(db, user, params, date_from, date_to)
    return Page(items=[_summary(s) for s in summaries], total=total, page=params.page, page_size=params.page_size)


@router.post("/summaries", response_model=SummaryResponse, status_code=status.HTTP_201_CREATED)
def create_summary(data: SummaryCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _summary(handbook_service.create_summary(db, user, data))


@router.patch("/summaries/{summary_id}", response_model=SummaryResponse)
def update_summary(
    summary_id: UUID, data: SummaryUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return _summary(handbook_service.update_summary(db, user, summary_id, data))


@router.get("/summaries/{summary_id}/versions", response_model=list[VersionResponse])
def summary_versions(summary_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [
        VersionResponse(version=v.version, snapshot=v.snapshot, edited_at=v.edited_at)
        for v in handbook_service.summary_versions(db, user, summary_id)
    ]
