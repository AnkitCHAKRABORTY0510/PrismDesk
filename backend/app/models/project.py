import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.columns import (
    created_at,
    optional_timestamp,
    updated_at,
    user_fk,
    uuid_pk,
)

PROJECT_STATUSES = ("active", "archived", "deleted")
MEMBERSHIP_ROLES = ("owner", "supervisor", "member", "guest")


class Project(Base):
    __tablename__ = "projects"

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'archived', 'deleted')",
            name="ck_projects_status",
        ),
        Index("ix_projects_status", "status"),
        Index("ix_projects_owner_id", "owner_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    objectives: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_by: Mapped[uuid.UUID | None] = user_fk(nullable=True)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", server_default="active"
    )

    archive_requested_by: Mapped[uuid.UUID | None] = user_fk(nullable=True)
    archive_requested_at: Mapped[datetime | None] = optional_timestamp()
    archive_request_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    archived_by: Mapped[uuid.UUID | None] = user_fk(nullable=True)
    archived_at: Mapped[datetime | None] = optional_timestamp()
    deleted_by: Mapped[uuid.UUID | None] = user_fk(nullable=True)
    deleted_at: Mapped[datetime | None] = optional_timestamp()

    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()

    owner: Mapped["User"] = relationship(foreign_keys=[owner_id])  # noqa: F821
    members: Mapped[list["ProjectMember"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ProjectMember(Base):
    """A user's role inside one project (separate from global roles).

    Supervising professors are members with ``membership_role='supervisor'``.
    Removed members keep their row with ``membership_status='removed'``
    so membership history survives.
    """

    __tablename__ = "project_members"

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
        CheckConstraint(
            "membership_role IN ('owner', 'supervisor', 'member', 'guest')",
            name="ck_project_members_role",
        ),
        CheckConstraint(
            "membership_status IN ('active', 'removed')",
            name="ck_project_members_status",
        ),
        Index("ix_project_members_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    membership_role: Mapped[str] = mapped_column(String(20), nullable=False)
    membership_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", server_default="active"
    )
    added_by: Mapped[uuid.UUID | None] = user_fk(nullable=True)
    joined_at: Mapped[datetime] = created_at()
    removed_at: Mapped[datetime | None] = optional_timestamp()
    updated_at: Mapped[datetime] = updated_at()

    project: Mapped[Project] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(foreign_keys=[user_id])  # noqa: F821
