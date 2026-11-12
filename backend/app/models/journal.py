import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.models.columns import created_at, updated_at, uuid_pk


class Journal(Base):
    """A journal on one user's personal list.

    Most journals accept submissions year round, so ``submission_deadline``
    is only set when the user tracks a special issue. Ranking fields are a
    snapshot taken when the journal was added (SCImago SJR / OpenAlex).
    """

    __tablename__ = "journals"

    __table_args__ = (
        Index("uq_journals_owner_title", "owner_id", "title_key", unique=True),
        Index(
            "uq_journals_owner_issn",
            "owner_id",
            "issn",
            unique=True,
            postgresql_where=text("issn IS NOT NULL"),
        ),
        Index("ix_journals_owner_deadline", "owner_id", "submission_deadline"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    # Lower-cased, punctuation-free title used to detect duplicates.
    title_key: Mapped[str] = mapped_column(String(300), nullable=False)
    issn: Mapped[str | None] = mapped_column(String(9), nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(300), nullable=True)
    homepage_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    sjr_quartile: Mapped[str | None] = mapped_column(String(2), nullable=True)
    sjr: Mapped[float | None] = mapped_column(Float, nullable=True)
    h_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    subject_areas: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    is_open_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    special_issue_title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    submission_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()
