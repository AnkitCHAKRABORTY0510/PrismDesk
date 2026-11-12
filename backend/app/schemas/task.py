from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from app.schemas.admin import UserSummary

TaskType = Literal["official", "personal", "reminder"]
TaskPriority = Literal["low", "medium", "high", "urgent"]
AssignmentStatus = Literal["todo", "in_progress", "under_review", "revision_required", "completed"]
ReviewDecision = Literal["approved", "revision_required"]


class TaskCreate(BaseModel):
    task_type: TaskType
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=20000)
    project_id: UUID | None = None
    priority: TaskPriority = "medium"
    due_at: datetime | None = None
    assignee_ids: list[UUID] = Field(default_factory=list, max_length=100)
    # Reminders: the task the reminder is about.
    related_task_id: UUID | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be empty.")
        return value

    @field_validator("due_at")
    @classmethod
    def aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("due_at must include a timezone offset.")
        return value

    @model_validator(mode="after")
    def check_type(self):
        if self.task_type == "official" and self.project_id is None:
            raise ValueError("Official tasks must belong to a project.")
        if self.task_type == "personal" and self.assignee_ids:
            raise ValueError("Personal tasks cannot be assigned to others.")
        if self.task_type == "reminder":
            if not self.assignee_ids:
                raise ValueError("Choose who should receive the reminder.")
            if self.project_id is None and self.related_task_id is None:
                raise ValueError("A reminder needs a project or a related task.")
        elif self.related_task_id is not None:
            raise ValueError("Only reminders can point at another task.")
        return self


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=20000)
    priority: TaskPriority | None = None
    due_at: datetime | None = None
    clear_due_at: bool = False


class AssigneesRequest(BaseModel):
    assignee_ids: list[UUID] = Field(min_length=1, max_length=100)


class StatusUpdate(BaseModel):
    status: AssignmentStatus


class SubmissionCreate(BaseModel):
    response_text: str = Field(default="", max_length=50000)
    links: list[HttpUrl] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def not_empty(self):
        if not self.response_text.strip() and not self.links:
            raise ValueError("A submission needs a text response or at least one link.")
        return self


class ReviewCreate(BaseModel):
    decision: ReviewDecision
    feedback: str = Field(default="", max_length=20000)

    @model_validator(mode="after")
    def feedback_for_revision(self):
        if self.decision == "revision_required" and not self.feedback.strip():
            raise ValueError("Explain what needs revision.")
        return self


class ReviewResponse(BaseModel):
    id: UUID
    reviewer: UserSummary | None
    decision: ReviewDecision
    feedback: str
    created_at: datetime


class SubmissionResponse(BaseModel):
    id: UUID
    assignment_id: UUID
    version: int
    response_text: str
    links: list[str]
    submitted_at: datetime
    reviews: list[ReviewResponse] = []


class AssignmentResponse(BaseModel):
    id: UUID
    task_id: UUID
    assignee: UserSummary
    status: AssignmentStatus
    assigned_at: datetime
    submitted_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime
    submission_count: int = 0


class TaskResponse(BaseModel):
    id: UUID
    task_type: TaskType
    title: str
    description: str
    project_id: UUID | None
    project_title: str | None = None
    created_by: UUID | None
    priority: TaskPriority
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime
    is_overdue: bool = False
    my_assignment: AssignmentResponse | None = None
    assignments: list[AssignmentResponse] = []
    can_manage: bool = False
    created_by_user: UserSummary | None = None
    related_task_id: UUID | None = None
    related_task_title: str | None = None


class ReminderRecipient(BaseModel):
    user: UserSummary
    membership_role: str


class PendingReviewResponse(BaseModel):
    assignment: AssignmentResponse
    task_id: UUID
    task_title: str
    project_id: UUID | None
    project_title: str | None
    latest_submission_id: UUID | None
    latest_version: int | None
    submitted_at: datetime | None
