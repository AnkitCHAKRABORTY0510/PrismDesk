"""Project-level authorization, evaluated on every project-scoped API.

Global roles say what kind of user someone is; project membership says
what they may do inside a particular project. Both are combined here so
every module (papers, tasks, handbook, conferences) shares one rule set.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, NotFoundError
from app.core.permissions import ADMINISTRATOR, PROFESSOR
from app.models.project import Project, ProjectMember
from app.models.user import User


@dataclass
class ProjectAccess:
    project: Project
    user: User
    membership: ProjectMember | None

    @property
    def is_admin(self) -> bool:
        return ADMINISTRATOR in self.user.role_names

    @property
    def role(self) -> str | None:
        return self.membership.membership_role if self.membership else None

    @property
    def is_active(self) -> bool:
        return self.project.status == "active"

    @property
    def can_view(self) -> bool:
        if self.project.status == "deleted":
            return self.is_admin
        return self.is_admin or self.membership is not None

    @property
    def is_manager(self) -> bool:
        """Administrators and professors who own or supervise the project."""

        return self.is_admin or (
            PROFESSOR in self.user.role_names
            and self.role in ("owner", "supervisor")
        )

    @property
    def is_supervisor(self) -> bool:
        return self.is_manager

    @property
    def can_edit_details(self) -> bool:
        return self.is_active and (self.is_manager or self.role == "owner")

    @property
    def can_contribute(self) -> bool:
        """Ordinary project activity: papers, entries, conferences, etc."""

        return self.is_active and (
            self.is_admin or self.role in ("owner", "supervisor", "member")
        )

    @property
    def can_manage_members(self) -> bool:
        return self.is_active and self.is_manager

    @property
    def can_archive(self) -> bool:
        return self.is_active and self.is_manager

    @property
    def can_unarchive(self) -> bool:
        return self.project.status == "archived" and self.is_manager

    @property
    def can_request_archive(self) -> bool:
        return (
            self.is_active
            and self.role == "owner"
            and not self.is_manager
            and self.project.archive_requested_at is None
        )

    @property
    def can_soft_delete(self) -> bool:
        return self.project.status != "deleted" and self.is_manager

    @property
    def can_restore(self) -> bool:
        return self.project.status == "deleted" and self.is_admin

    def flags(self) -> dict[str, bool]:
        return {
            "can_edit": self.can_edit_details,
            "can_contribute": self.can_contribute,
            "can_manage_members": self.can_manage_members,
            "can_archive": self.can_archive,
            "can_unarchive": self.can_unarchive,
            "can_request_archive": self.can_request_archive,
            "can_delete": self.can_soft_delete,
            "can_restore": self.can_restore,
            "can_review": self.is_manager and self.is_active,
        }


def get_membership(db: Session, project_id: UUID, user_id: UUID) -> ProjectMember | None:
    return db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
            ProjectMember.membership_status == "active",
        )
    )


def get_project_access(
    db: Session,
    user: User,
    project_id: UUID,
    lock: bool = False,
) -> ProjectAccess:
    """Load a project and the caller's rights, or 404 if not visible.

    A 404 (not 403) is returned for projects the user cannot see so the
    API does not reveal which project IDs exist.
    """

    statement = select(Project).where(Project.id == project_id)
    if lock:
        statement = statement.with_for_update()

    project = db.scalar(statement)

    if not project:
        raise NotFoundError("Project not found.")

    access = ProjectAccess(
        project=project,
        user=user,
        membership=get_membership(db, project_id, user.id),
    )

    if not access.can_view:
        raise NotFoundError("Project not found.")

    return access


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ForbiddenError(message)


def visible_project_ids(user: User) -> Select:
    """Subquery of project IDs (not deleted) the user may read."""

    if ADMINISTRATOR in user.role_names:
        return select(Project.id).where(Project.status != "deleted")

    return (
        select(ProjectMember.project_id)
        .join(Project, Project.id == ProjectMember.project_id)
        .where(
            ProjectMember.user_id == user.id,
            ProjectMember.membership_status == "active",
            Project.status != "deleted",
        )
    )


def managed_project_ids(user: User) -> Select:
    """Subquery of non-deleted projects the user supervises or manages."""

    if ADMINISTRATOR in user.role_names:
        return select(Project.id).where(Project.status != "deleted")

    if PROFESSOR not in user.role_names:
        return select(Project.id).where(Project.id.is_(None))

    return (
        select(ProjectMember.project_id)
        .join(Project, Project.id == ProjectMember.project_id)
        .where(
            ProjectMember.user_id == user.id,
            ProjectMember.membership_status == "active",
            ProjectMember.membership_role.in_(("owner", "supervisor")),
            Project.status != "deleted",
        )
    )
