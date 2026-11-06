import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.models.columns import created_at, optional_timestamp, updated_at, user_fk, uuid_pk


class Conference(Base):
    """A conference edition. Stored once and linked to many projects.

    All timestamps are stored in UTC (timestamptz); the browser renders
    them in the viewer's timezone.
    """

    __tablename__ = "conferences"

    __table_args__ = (
        Index(
            "uq_conferences_name_deadline",
            text("lower(name)"),
            "submission_deadline",
            unique=True,
        ),
        Index("ix_conferences_submission_deadline", "submission_deadline"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    acronym: Mapped[str | None] = mapped_column(String(50), nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    cfp_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    submission_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    important_dates: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    added_by: Mapped[uuid.UUID | None] = user_fk(nullable=True)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()


class ProjectConference(Base):
    __tablename__ = "project_conferences"

    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived')", name="ck_project_conferences_status"),
        Index("ix_project_conferences_conference_id", "conference_id"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    conference_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conferences.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")
    added_by: Mapped[uuid.UUID | None] = user_fk(nullable=True)
    added_at: Mapped[datetime] = created_at()
    archived_by: Mapped[uuid.UUID | None] = user_fk(nullable=True)
    archived_at: Mapped[datetime | None] = optional_timestamp()
