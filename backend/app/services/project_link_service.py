"""GitHub repository links on projects.

Any active member (owner, supervisor or member — not guests) of an active
project may add a link. The person who added a link, or a project manager,
may remove it. Archived projects are read-only.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models.project_link import ProjectRepoLink
from app.models.user import User
from app.schemas.project_link import RepoLinkCreate, RepoLinkResponse
from app.services.audit_service import record_audit
from app.services.project_access import ProjectAccess, get_project_access, require

CONTRIBUTOR_ROLES = ("owner", "supervisor", "member")


def can_add(access: ProjectAccess) -> bool:
    return access.is_active and (access.role in CONTRIBUTOR_ROLES or access.is_manager)


def can_remove(access: ProjectAccess, link: ProjectRepoLink) -> bool:
    if not access.is_active:
        return False
    return access.is_manager or (link.added_by == access.user.id and access.role in CONTRIBUTOR_ROLES)


def _response(access: ProjectAccess, link: ProjectRepoLink, username: str | None) -> RepoLinkResponse:
    return RepoLinkResponse(
        id=link.id,
        project_id=link.project_id,
        url=link.url,
        label=link.label,
        added_by=link.added_by,
        added_by_username=username,
        created_at=link.created_at,
        can_remove=can_remove(access, link),
    )


def list_links(db: Session, user: User, project_id: UUID) -> list[RepoLinkResponse]:
    access = get_project_access(db, user, project_id)
    rows = db.execute(
        select(ProjectRepoLink, User.username)
        .outerjoin(User, User.id == ProjectRepoLink.added_by)
        .where(ProjectRepoLink.project_id == project_id)
        .order_by(ProjectRepoLink.created_at)
    ).all()
    return [_response(access, link, username) for link, username in rows]


def add_link(db: Session, user: User, project_id: UUID, data: RepoLinkCreate) -> RepoLinkResponse:
    access = get_project_access(db, user, project_id)
    require(access.is_active, "Archived projects are read-only.")
    require(can_add(access), "Only project members can add repository links.")

    exists = db.scalar(
        select(ProjectRepoLink.id).where(ProjectRepoLink.project_id == project_id, ProjectRepoLink.url == data.url)
    )
    if exists:
        raise ConflictError("This repository is already linked to the project.")

    link = ProjectRepoLink(project_id=project_id, url=data.url, label=data.label, added_by=user.id)
    db.add(link)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("This repository is already linked to the project.") from exc

    record_audit(
        db, user.id, "project.repo_link_added", "project", project_id, {"link_id": link.id, "url": link.url}
    )
    db.commit()
    db.refresh(link)
    return _response(access, link, user.username)


def remove_link(db: Session, user: User, project_id: UUID, link_id: UUID) -> None:
    access = get_project_access(db, user, project_id)
    link = db.get(ProjectRepoLink, link_id)
    if not link or link.project_id != project_id:
        raise NotFoundError("Repository link not found.")
    require(access.is_active, "Archived projects are read-only.")
    require(can_remove(access, link), "Only the person who added the link or a project supervisor can remove it.")

    record_audit(
        db, user.id, "project.repo_link_removed", "project", project_id, {"link_id": link.id, "url": link.url}
    )
    db.delete(link)
    db.commit()
