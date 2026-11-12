import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.models.columns import created_at, user_fk, uuid_pk


class ProjectRepoLink(Base):
    """A GitHub repository linked to a project.

    Prism Desk only stores the URL; code lives on GitHub. The URL is
    normalised (no trailing slash or ``.git``) before it is stored, so the
    unique constraint catches duplicates of the same repository.
    """

    __tablename__ = "project_repo_links"

    __table_args__ = (
        UniqueConstraint("project_id", "url", name="uq_project_repo_links_project_url"),
        Index("ix_project_repo_links_project_id", "project_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    added_by: Mapped[uuid.UUID | None] = user_fk(nullable=True)
    created_at: Mapped[datetime] = created_at()
