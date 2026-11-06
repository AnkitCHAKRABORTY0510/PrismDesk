import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.columns import created_at, updated_at, user_fk, uuid_pk

READING_STATUSES = ("not_started", "reading", "completed")


class ResearchPaper(Base):
    """Central metadata record. Prism Desk never stores paper files."""

    __tablename__ = "research_papers"

    __table_args__ = (
        Index(
            "uq_research_papers_doi_lower",
            text("lower(doi)"),
            unique=True,
            postgresql_where=text("doi IS NOT NULL"),
        ),
        Index("ix_research_papers_publication_year", "publication_year"),
        Index("ix_research_papers_authors", "authors", postgresql_using="gin"),
        Index("ix_research_papers_keywords", "keywords", postgresql_using="gin"),
        CheckConstraint(
            "publication_year IS NULL OR publication_year BETWEEN 1800 AND 2200",
            name="ck_research_papers_year",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    authors: Mapped[list[str]] = mapped_column(
        ARRAY(String(200)), nullable=False, default=list, server_default="{}"
    )
    abstract: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    venue: Mapped[str | None] = mapped_column(String(300), nullable=True)
    doi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    keywords: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)), nullable=False, default=list, server_default="{}"
    )
    added_by: Mapped[uuid.UUID | None] = user_fk(nullable=True)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()

    project_links: Mapped[list["ProjectPaper"]] = relationship(
        back_populates="paper", cascade="all, delete-orphan", passive_deletes=True
    )


class ProjectPaper(Base):
    __tablename__ = "project_papers"

    __table_args__ = (Index("ix_project_papers_paper_id", "paper_id"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_papers.id", ondelete="CASCADE"), primary_key=True
    )
    added_by: Mapped[uuid.UUID | None] = user_fk(nullable=True)
    added_at: Mapped[datetime] = created_at()

    paper: Mapped[ResearchPaper] = relationship(back_populates="project_links")


class PaperReadingProgress(Base):
    """One reading status per student, paper and (optional) project."""

    __tablename__ = "paper_reading_progress"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "paper_id",
            "project_id",
            name="uq_paper_reading_progress_user_paper_project",
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint(
            "status IN ('not_started', 'reading', 'completed')",
            name="ck_paper_reading_progress_status",
        ),
        Index("ix_paper_reading_progress_paper_id", "paper_id"),
        Index("ix_paper_reading_progress_project_id", "project_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_papers.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="not_started", server_default="not_started"
    )
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()


class ResearchNote(Base):
    """Private note: readable and writable only by its author."""

    __tablename__ = "research_notes"

    __table_args__ = (Index("ix_research_notes_user_paper", "user_id", "paper_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_papers.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()
