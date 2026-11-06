from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, model_validator

from app.schemas.admin import UserSummary

TEXT_LIMIT = 20000


class EntryFields(BaseModel):
    work_completed: str = Field(default="", max_length=TEXT_LIMIT)
    research_progress: str = Field(default="", max_length=TEXT_LIMIT)
    problems: str = Field(default="", max_length=TEXT_LIMIT)
    next_steps: str = Field(default="", max_length=TEXT_LIMIT)
    references: list[HttpUrl] = Field(default_factory=list, max_length=20)


class EntryCreate(EntryFields):
    project_id: UUID
    entry_date: date

    @model_validator(mode="after")
    def has_content(self):
        if not any(
            getattr(self, field).strip()
            for field in ("work_completed", "research_progress", "problems", "next_steps")
        ):
            raise ValueError("Describe at least one part of the day's work.")
        return self


class EntryUpdate(BaseModel):
    work_completed: str | None = Field(default=None, max_length=TEXT_LIMIT)
    research_progress: str | None = Field(default=None, max_length=TEXT_LIMIT)
    problems: str | None = Field(default=None, max_length=TEXT_LIMIT)
    next_steps: str | None = Field(default=None, max_length=TEXT_LIMIT)
    references: list[HttpUrl] | None = Field(default=None, max_length=20)


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    parent_id: UUID | None = None


class CommentResponse(BaseModel):
    id: UUID
    entry_id: UUID
    parent_id: UUID | None
    author: UserSummary | None
    body: str
    created_at: datetime
    replies: list["CommentResponse"] = []


class EntryResponse(BaseModel):
    id: UUID
    student: UserSummary
    project_id: UUID
    project_title: str | None = None
    entry_date: date
    work_completed: str
    research_progress: str
    problems: str
    next_steps: str
    references: list[str]
    version: int
    created_at: datetime
    updated_at: datetime
    comment_count: int = 0
    comments: list[CommentResponse] = []
    can_edit: bool = False
    can_comment: bool = False


class VersionResponse(BaseModel):
    version: int
    snapshot: dict
    edited_at: datetime


class SummaryCreate(BaseModel):
    entry_date: date
    summary: str = Field(min_length=1, max_length=TEXT_LIMIT)
    challenges: str = Field(default="", max_length=TEXT_LIMIT)
    plan_next: str = Field(default="", max_length=TEXT_LIMIT)


class SummaryUpdate(BaseModel):
    summary: str | None = Field(default=None, min_length=1, max_length=TEXT_LIMIT)
    challenges: str | None = Field(default=None, max_length=TEXT_LIMIT)
    plan_next: str | None = Field(default=None, max_length=TEXT_LIMIT)


class SummaryResponse(BaseModel):
    id: UUID
    entry_date: date
    summary: str
    challenges: str
    plan_next: str
    version: int
    created_at: datetime
    updated_at: datetime


class ProgressDay(BaseModel):
    entry_date: date
    entry_count: int
    student_count: int
