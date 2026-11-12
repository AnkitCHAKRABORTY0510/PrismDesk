"""Schemas for handbook shared notes (the part of a day shared with supervisors)."""

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, Field

from app.schemas.admin import UserSummary


def _strip_required(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("The shared note cannot be empty.")
    return value


NoteBody = Annotated[str, Field(min_length=1, max_length=20000), AfterValidator(_strip_required)]


class SharedNoteCreate(BaseModel):
    entry_date: date
    body: NoteBody


class SharedNoteUpdate(BaseModel):
    body: NoteBody


class SharedCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    parent_id: UUID | None = None


class SharedCommentResponse(BaseModel):
    id: UUID
    note_id: UUID
    parent_id: UUID | None
    author: UserSummary | None
    body: str
    created_at: datetime
    replies: list["SharedCommentResponse"] = []


class SharedNoteResponse(BaseModel):
    id: UUID
    student: UserSummary
    entry_date: date
    body: str
    version: int
    created_at: datetime
    updated_at: datetime
    comment_count: int = 0
    comments: list[SharedCommentResponse] = []
    can_edit: bool = False
    can_comment: bool = False
