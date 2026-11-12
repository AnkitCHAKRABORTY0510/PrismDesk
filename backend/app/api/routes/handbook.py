from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, page_params, require_capability
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
from app.schemas.handbook_planner import (
    PinCreate,
    PinResponse,
    PinUpdate,
    PlannerRange,
    ReminderCreate,
    ReminderResponse,
    ReminderUpdate,
    TodoCarryForward,
    TodoCreate,
    TodoReorder,
    TodoResponse,
    TodoUpdate,
)
from app.schemas.handbook_shared import (
    SharedCommentCreate,
    SharedNoteCreate,
    SharedNoteResponse,
    SharedNoteUpdate,
)
from app.services import handbook_planner_service as planner
from app.services import handbook_shared_service as shared
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


# --- Personal planner: pins, to-dos, reminders (owner-only) ---------------------------

planner_user = require_capability("handbook.view")


def _pin(pin) -> PinResponse:
    return PinResponse.model_validate(pin, from_attributes=True)


def _todo(todo) -> TodoResponse:
    return TodoResponse.model_validate(todo, from_attributes=True)


def _reminder(reminder) -> ReminderResponse:
    return ReminderResponse.model_validate(reminder, from_attributes=True)


@router.get("/planner", response_model=PlannerRange)
def planner_range(
    date_from: date,
    date_to: date,
    db: Session = Depends(get_db),
    user: User = Depends(planner_user),
):
    pins, todos, reminders = planner.planner_range(db, user, date_from, date_to)
    return PlannerRange(
        pins=[_pin(p) for p in pins],
        todos=[_todo(t) for t in todos],
        reminders=[_reminder(r) for r in reminders],
    )


@router.post("/pins", response_model=PinResponse, status_code=status.HTTP_201_CREATED)
def create_pin(data: PinCreate, db: Session = Depends(get_db), user: User = Depends(planner_user)):
    return _pin(planner.create_pin(db, user, data))


@router.patch("/pins/{pin_id}", response_model=PinResponse)
def update_pin(pin_id: UUID, data: PinUpdate, db: Session = Depends(get_db), user: User = Depends(planner_user)):
    return _pin(planner.update_pin(db, user, pin_id, data))


@router.delete("/pins/{pin_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pin(pin_id: UUID, db: Session = Depends(get_db), user: User = Depends(planner_user)):
    planner.delete_pin(db, user, pin_id)


@router.get("/todos/open", response_model=list[TodoResponse])
def open_todos(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(planner_user),
):
    return [_todo(t) for t in planner.open_todos(db, user, limit)]


@router.post("/todos", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
def create_todo(data: TodoCreate, db: Session = Depends(get_db), user: User = Depends(planner_user)):
    return _todo(planner.create_todo(db, user, data))


@router.post("/todos/reorder", response_model=list[TodoResponse])
def reorder_todos(data: TodoReorder, db: Session = Depends(get_db), user: User = Depends(planner_user)):
    return [_todo(t) for t in planner.reorder_todos(db, user, data)]


@router.post("/todos/carry-forward", response_model=list[TodoResponse])
def carry_forward(data: TodoCarryForward, db: Session = Depends(get_db), user: User = Depends(planner_user)):
    return [_todo(t) for t in planner.carry_forward(db, user, data)]


@router.patch("/todos/{todo_id}", response_model=TodoResponse)
def update_todo(todo_id: UUID, data: TodoUpdate, db: Session = Depends(get_db), user: User = Depends(planner_user)):
    return _todo(planner.update_todo(db, user, todo_id, data))


@router.delete("/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id: UUID, db: Session = Depends(get_db), user: User = Depends(planner_user)):
    planner.delete_todo(db, user, todo_id)


@router.get("/reminders/upcoming", response_model=list[ReminderResponse])
def upcoming_reminders(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(planner_user),
):
    return [_reminder(r) for r in planner.upcoming_reminders(db, user, limit)]


@router.post("/reminders", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
def create_reminder(data: ReminderCreate, db: Session = Depends(get_db), user: User = Depends(planner_user)):
    return _reminder(planner.create_reminder(db, user, data))


@router.patch("/reminders/{reminder_id}", response_model=ReminderResponse)
def update_reminder(
    reminder_id: UUID, data: ReminderUpdate, db: Session = Depends(get_db), user: User = Depends(planner_user)
):
    return _reminder(planner.update_reminder(db, user, reminder_id, data))


@router.delete("/reminders/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reminder(reminder_id: UUID, db: Session = Depends(get_db), user: User = Depends(planner_user)):
    planner.delete_reminder(db, user, reminder_id)


# --- Shared notes: written by a student for their supervisors ------------------------


def _shared(db, user, note) -> SharedNoteResponse:
    return shared.note_responses(db, user, [note], with_comments=True)[0]


@router.get("/shared-notes", response_model=Page[SharedNoteResponse])
def list_shared_notes(
    date_from: date | None = None,
    date_to: date | None = None,
    student_id: UUID | None = None,
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    user: User = Depends(planner_user),
):
    notes, total = shared.list_notes(db, user, params, date_from, date_to, student_id)
    return Page(items=shared.note_responses(db, user, notes), total=total, page=params.page, page_size=params.page_size)


@router.post("/shared-notes", response_model=SharedNoteResponse, status_code=status.HTTP_201_CREATED)
def create_shared_note(data: SharedNoteCreate, db: Session = Depends(get_db), user: User = Depends(planner_user)):
    return _shared(db, user, shared.create_note(db, user, data))


@router.get("/shared-notes/{note_id}", response_model=SharedNoteResponse)
def get_shared_note(note_id: UUID, db: Session = Depends(get_db), user: User = Depends(planner_user)):
    return _shared(db, user, shared.get_note(db, user, note_id))


@router.patch("/shared-notes/{note_id}", response_model=SharedNoteResponse)
def update_shared_note(
    note_id: UUID, data: SharedNoteUpdate, db: Session = Depends(get_db), user: User = Depends(planner_user)
):
    return _shared(db, user, shared.update_note(db, user, note_id, data))


@router.get("/shared-notes/{note_id}/versions", response_model=list[VersionResponse])
def shared_note_versions(note_id: UUID, db: Session = Depends(get_db), user: User = Depends(planner_user)):
    return [
        VersionResponse(version=v.version, snapshot=v.snapshot, edited_at=v.edited_at)
        for v in shared.note_versions(db, user, note_id)
    ]


@router.post("/shared-notes/{note_id}/comments", response_model=SharedNoteResponse, status_code=status.HTTP_201_CREATED)
def add_shared_comment(
    note_id: UUID, data: SharedCommentCreate, db: Session = Depends(get_db), user: User = Depends(planner_user)
):
    shared.add_comment(db, user, note_id, data.body, data.parent_id)
    return _shared(db, user, shared.get_note(db, user, note_id))
