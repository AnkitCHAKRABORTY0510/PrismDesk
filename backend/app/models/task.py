import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.columns import created_at, optional_timestamp, updated_at, user_fk, uuid_pk

TASK_TYPES = ("official", "personal")
TASK_PRIORITIES = ("low", "medium", "high", "urgent")
ASSIGNMENT_STATUSES = ("todo", "in_progress", "under_review", "revision_required", "completed")


class Task(Base):
    __tablename__ = "tasks"

    __table_args__ = (
        CheckConstraint("task_type IN ('official', 'personal')", name="ck_tasks_type"),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'urgent')", name="ck_tasks_priority"
        ),
        CheckConstraint(
            "task_type = 'personal' OR project_id IS NOT NULL",
            name="ck_tasks_official_has_project",
        ),
        Index("ix_tasks_project_id", "project_id"),
        Index("ix_tasks_created_by", "created_by"),
        Index("ix_tasks_due_at", "due_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    task_type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = user_fk(nullable=True)
    priority: Mapped[str] = mapped_column(
        String(10), nullable=False, default="medium", server_default="medium"
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()

    assignments: Mapped[list["TaskAssignment"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", passive_deletes=True
    )


class TaskAssignment(Base):
    """One student's independent copy of a task: status and submissions."""

    __tablename__ = "task_assignments"

    __table_args__ = (
        UniqueConstraint("task_id", "assignee_id", name="uq_task_assignments_task_assignee"),
        CheckConstraint(
            "status IN ('todo', 'in_progress', 'under_review', 'revision_required', 'completed')",
            name="ck_task_assignments_status",
        ),
        Index("ix_task_assignments_assignee_status", "assignee_id", "status"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    assignee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="todo", server_default="todo")
    assigned_by: Mapped[uuid.UUID | None] = user_fk(nullable=True)
    assigned_at: Mapped[datetime] = created_at()
    submitted_at: Mapped[datetime | None] = optional_timestamp()
    completed_at: Mapped[datetime | None] = optional_timestamp()
    updated_at: Mapped[datetime] = updated_at()

    task: Mapped[Task] = relationship(back_populates="assignments")
    assignee: Mapped["User"] = relationship(foreign_keys=[assignee_id])  # noqa: F821
    submissions: Mapped[list["TaskSubmission"]] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="TaskSubmission.version",
    )


class TaskSubmission(Base):
    """An immutable submission version (text and external links only)."""

    __tablename__ = "task_submissions"

    __table_args__ = (
        UniqueConstraint("assignment_id", "version", name="uq_task_submissions_assignment_version"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_assignments.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    links: Mapped[list[str]] = mapped_column(
        ARRAY(String(2048)), nullable=False, default=list, server_default="{}"
    )
    submitted_by: Mapped[uuid.UUID | None] = user_fk(nullable=True)
    submitted_at: Mapped[datetime] = created_at()

    assignment: Mapped[TaskAssignment] = relationship(back_populates="submissions")
    reviews: Mapped[list["TaskReview"]] = relationship(
        back_populates="submission",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="TaskReview.created_at",
    )


class TaskReview(Base):
    __tablename__ = "task_reviews"

    __table_args__ = (
        CheckConstraint(
            "decision IN ('approved', 'revision_required')", name="ck_task_reviews_decision"
        ),
        Index("ix_task_reviews_submission_id", "submission_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_submissions.id", ondelete="CASCADE"), nullable=False
    )
    reviewer_id: Mapped[uuid.UUID | None] = user_fk(nullable=True)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = created_at()

    submission: Mapped[TaskSubmission] = relationship(back_populates="reviews")
