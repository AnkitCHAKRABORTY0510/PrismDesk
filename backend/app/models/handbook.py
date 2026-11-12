import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.columns import created_at, updated_at, user_fk, uuid_pk


class HandbookEntry(Base):
    """A student's daily entry for one project (one per project per day)."""

    __tablename__ = "handbook_entries"

    __table_args__ = (
        UniqueConstraint(
            "student_id", "project_id", "entry_date", name="uq_handbook_entries_student_project_date"
        ),
        Index("ix_handbook_entries_project_date", "project_id", "entry_date"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    work_completed: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    research_progress: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    problems: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    next_steps: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    references: Mapped[list[str]] = mapped_column(
        ARRAY(String(2048)), nullable=False, default=list, server_default="{}"
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()

    student: Mapped["User"] = relationship(foreign_keys=[student_id])  # noqa: F821


class HandbookEntryVersion(Base):
    """Snapshot of every saved version of a project entry."""

    __tablename__ = "handbook_entry_versions"

    __table_args__ = (
        UniqueConstraint("entry_id", "version", name="uq_handbook_entry_versions_entry_version"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("handbook_entries.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    edited_by: Mapped[uuid.UUID | None] = user_fk(nullable=True)
    edited_at: Mapped[datetime] = created_at()


class DailySummary(Base):
    """A student's overall daily summary. Private to the student."""

    __tablename__ = "daily_summaries"

    __table_args__ = (
        UniqueConstraint("student_id", "entry_date", name="uq_daily_summaries_student_date"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    challenges: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    plan_next: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()


class DailySummaryVersion(Base):
    __tablename__ = "daily_summary_versions"

    __table_args__ = (
        UniqueConstraint("summary_id", "version", name="uq_daily_summary_versions_summary_version"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    summary_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("daily_summaries.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    edited_at: Mapped[datetime] = created_at()


class HandbookComment(Base):
    """Supervisor comment on an entry; replies point at a top-level comment."""

    __tablename__ = "handbook_comments"

    __table_args__ = (
        Index("ix_handbook_comments_entry_id", "entry_id"),
        Index("ix_handbook_comments_parent_id", "parent_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("handbook_entries.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("handbook_comments.id", ondelete="CASCADE"), nullable=True
    )
    author_id: Mapped[uuid.UUID | None] = user_fk(nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()

    author: Mapped["User"] = relationship(foreign_keys=[author_id])  # noqa: F821


# --- Personal planner: pins, to-dos and reminders --------------------------------
# Owned by one user and visible only to them. Unlike entries and summaries
# these may be dated in the future (they are for planning).

PIN_CATEGORIES = ("deadline", "meeting", "milestone", "idea", "other")


class HandbookPin(Base):
    """A coloured marker on one calendar day."""

    __tablename__ = "handbook_pins"

    __table_args__ = (
        CheckConstraint(
            "category IN ('deadline', 'meeting', 'milestone', 'idea', 'other')",
            name="ck_handbook_pins_category",
        ),
        Index("ix_handbook_pins_owner_date", "owner_id", "pin_date"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    pin_date: Mapped[date] = mapped_column(Date, nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False, default="other", server_default="other")
    note: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()


class HandbookTodo(Base):
    """A to-do item planned for one day; ``position`` orders a day's list."""

    __tablename__ = "handbook_todos"

    __table_args__ = (Index("ix_handbook_todos_owner_date", "owner_id", "todo_date"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    todo_date: Mapped[date] = mapped_column(Date, nullable=False)
    text: Mapped[str] = mapped_column(String(500), nullable=False)
    done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()


class HandbookReminder(Base):
    """A timed reminder. ``reminder_date`` is the user's local calendar day."""

    __tablename__ = "handbook_reminders"

    __table_args__ = (
        Index("ix_handbook_reminders_owner_date", "owner_id", "reminder_date"),
        Index("ix_handbook_reminders_owner_remind_at", "owner_id", "remind_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    reminder_date: Mapped[date] = mapped_column(Date, nullable=False)
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    note: Mapped[str] = mapped_column(String(500), nullable=False)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()


# --- Shared notes: the part of a student's day written for supervisors -------------


class HandbookSharedNote(Base):
    """A student's note for one day that their supervisors can read and comment on.

    Kept apart from ``DailySummary`` so the private journal can never leak
    through a shared-note query.
    """

    __tablename__ = "handbook_shared_notes"

    __table_args__ = (
        UniqueConstraint("student_id", "entry_date", name="uq_handbook_shared_notes_student_date"),
        Index("ix_handbook_shared_notes_date", "entry_date"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()

    student: Mapped["User"] = relationship(foreign_keys=[student_id])  # noqa: F821


class HandbookSharedNoteVersion(Base):
    __tablename__ = "handbook_shared_note_versions"

    __table_args__ = (
        UniqueConstraint("note_id", "version", name="uq_handbook_shared_note_versions_note_version"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("handbook_shared_notes.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    edited_at: Mapped[datetime] = created_at()


class HandbookSharedNoteComment(Base):
    """Supervisor comment on a shared note; replies point at a top-level comment."""

    __tablename__ = "handbook_shared_note_comments"

    __table_args__ = (
        Index("ix_handbook_shared_note_comments_note_id", "note_id"),
        Index("ix_handbook_shared_note_comments_parent_id", "parent_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("handbook_shared_notes.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("handbook_shared_note_comments.id", ondelete="CASCADE"), nullable=True
    )
    author_id: Mapped[uuid.UUID | None] = user_fk(nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()

    author: Mapped["User"] = relationship(foreign_keys=[author_id])  # noqa: F821
