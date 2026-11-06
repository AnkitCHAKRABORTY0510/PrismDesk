import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
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
