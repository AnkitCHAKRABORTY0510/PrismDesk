from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.errors import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import ADMINISTRATOR, GUEST, PROFESSOR, has_capability
from app.models.project import Project, ProjectMember
from app.models.user import User
from app.schemas.admin import user_summary
from app.schemas.common import PageParams, paginate
from app.schemas.project import (
    ProjectCreate,
    ProjectPermissions,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.audit_service import record_audit
from app.services.notification_service import enqueue_notification
from app.services.project_access import (
    ProjectAccess,
    get_project_access,
    require,
    visible_project_ids,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _commit(db: Session):
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def purge_eligible_at(project: Project) -> datetime | None:
    if project.deleted_at is None:
        return None
    return project.deleted_at + timedelta(days=settings.PROJECT_DELETE_RETENTION_DAYS)


def project_response(db: Session, access: ProjectAccess) -> ProjectResponse:
    project = access.project

    active_members = db.scalars(
        select(ProjectMember)
        .options(selectinload(ProjectMember.user))
        .where(
            ProjectMember.project_id == project.id,
            ProjectMember.membership_status == "active",
        )
    ).all()

    return ProjectResponse(
        id=project.id,
        title=project.title,
        description=project.description,
        objectives=project.objectives,
        status=project.status,
        owner=user_summary(project.owner),
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
        archive_requested_at=project.archive_requested_at,
        archive_request_reason=project.archive_request_reason,
        archived_at=project.archived_at,
        deleted_at=project.deleted_at,
        purge_eligible_at=purge_eligible_at(project),
        member_count=len(active_members),
        supervisors=[
            user_summary(member.user)
            for member in active_members
            if member.membership_role == "supervisor"
        ],
        my_role=access.role,
        permissions=ProjectPermissions(**access.flags()),
    )


def _notify_project_members(
    db: Session,
    project: Project,
    event_type: str,
    title: str,
    body: str,
    dedupe_suffix: str,
    roles: tuple[str, ...] = ("owner", "supervisor", "member"),
    exclude: UUID | None = None,
):
    member_ids = db.scalars(
        select(ProjectMember.user_id).where(
            ProjectMember.project_id == project.id,
            ProjectMember.membership_status == "active",
            ProjectMember.membership_role.in_(roles),
        )
    ).all()

    for member_id in member_ids:
        if member_id == exclude:
            continue
        enqueue_notification(
            db,
            recipient_id=member_id,
            category="projects",
            event_type=event_type,
            title=title,
            body=body,
            entity_type="project",
            entity_id=project.id,
            dedupe_key=f"{event_type}:{project.id}:{member_id}:{dedupe_suffix}",
        )


# --- Creation and listing ----------------------------------------------------


def create_project(db: Session, user: User, data: ProjectCreate) -> ProjectAccess:
    if not has_capability(user.role_names, "projects.create"):
        raise ForbiddenError("You do not have permission to create projects.")

    project = Project(
        title=data.title,
        description=data.description,
        objectives=data.objectives,
        owner_id=user.id,
        created_by=user.id,
        status="active",
    )
    db.add(project)
    db.flush()

    membership = ProjectMember(
        project_id=project.id,
        user_id=user.id,
        membership_role="owner",
        added_by=user.id,
    )
    db.add(membership)

    record_audit(db, user.id, "project.created", "project", project.id, {"title": project.title})

    # Let administrators know a new project exists.
    admin_ids = db.scalars(
        select(User.id).where(
            User.account_status == "approved",
            User.roles.any(name=ADMINISTRATOR),
            User.id != user.id,
        )
    ).all()
    for admin_id in admin_ids:
        enqueue_notification(
            db,
            recipient_id=admin_id,
            category="projects",
            event_type="project.created",
            title="New project created",
            body=f"{user.full_name} created the project “{project.title}”.",
            entity_type="project",
            entity_id=project.id,
            dedupe_key=f"project.created:{project.id}:{admin_id}",
        )

    _commit(db)
    db.refresh(project)

    return ProjectAccess(project=project, user=user, membership=membership)


def list_projects(
    db: Session,
    user: User,
    params: PageParams,
    status: str | None = None,
    search: str | None = None,
    mine: bool = False,
    member_user_id: UUID | None = None,
) -> tuple[list[Project], int]:
    is_admin = ADMINISTRATOR in user.role_names

    statement = select(Project).options(selectinload(Project.owner)).order_by(Project.updated_at.desc())

    if status == "deleted":
        if not is_admin:
            raise ForbiddenError("Only administrators can view deleted projects.")
        statement = statement.where(Project.status == "deleted")
    else:
        statement = statement.where(Project.id.in_(visible_project_ids(user)))
        if status:
            statement = statement.where(Project.status == status)

    if mine or member_user_id:
        target = member_user_id or user.id
        if target != user.id and not is_admin:
            raise ForbiddenError("Only administrators can view another user's projects.")
        statement = statement.where(
            Project.id.in_(
                select(ProjectMember.project_id).where(
                    ProjectMember.user_id == target,
                    ProjectMember.membership_status == "active",
                )
            )
        )

    if search and search.strip():
        term = f"%{search.strip()}%"
        statement = statement.where(or_(Project.title.ilike(term), Project.description.ilike(term)))

    return paginate(db, statement, params)


def build_accesses(db: Session, user: User, projects: list[Project]) -> list[ProjectAccess]:
    if not projects:
        return []

    memberships = {
        member.project_id: member
        for member in db.scalars(
            select(ProjectMember).where(
                ProjectMember.user_id == user.id,
                ProjectMember.membership_status == "active",
                ProjectMember.project_id.in_([project.id for project in projects]),
            )
        ).all()
    }

    return [
        ProjectAccess(project=project, user=user, membership=memberships.get(project.id))
        for project in projects
    ]


def summary_responses(db: Session, accesses: list[ProjectAccess]) -> list[ProjectResponse]:
    if not accesses:
        return []

    ids = [access.project.id for access in accesses]
    counts = dict(
        db.execute(
            select(ProjectMember.project_id, func.count())
            .where(
                ProjectMember.project_id.in_(ids),
                ProjectMember.membership_status == "active",
            )
            .group_by(ProjectMember.project_id)
        ).all()
    )

    responses = []
    for access in accesses:
        project = access.project
        responses.append(
            ProjectResponse(
                id=project.id,
                title=project.title,
                description=project.description,
                objectives=project.objectives,
                status=project.status,
                owner=user_summary(project.owner),
                created_by=project.created_by,
                created_at=project.created_at,
                updated_at=project.updated_at,
                archive_requested_at=project.archive_requested_at,
                archive_request_reason=project.archive_request_reason,
                archived_at=project.archived_at,
                deleted_at=project.deleted_at,
                purge_eligible_at=purge_eligible_at(project),
                member_count=counts.get(project.id, 0),
                my_role=access.role,
                permissions=ProjectPermissions(**access.flags()),
            )
        )
    return responses


# --- Project details and lifecycle ---------------------------------------------


def update_project(db: Session, user: User, project_id: UUID, data: ProjectUpdate) -> ProjectAccess:
    access = get_project_access(db, user, project_id, lock=True)
    require(access.can_edit_details, "You cannot edit this project.")

    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in changes.items():
        setattr(access.project, field, value)

    if changes:
        record_audit(db, user.id, "project.updated", "project", project_id, {"fields": sorted(changes)})

    _commit(db)
    db.refresh(access.project)
    return access


def request_archive(db: Session, user: User, project_id: UUID, reason: str) -> ProjectAccess:
    access = get_project_access(db, user, project_id, lock=True)
    require(access.can_request_archive, "You cannot request archival of this project.")

    project = access.project
    project.archive_requested_by = user.id
    project.archive_requested_at = _now()
    project.archive_request_reason = reason.strip() or None

    record_audit(db, user.id, "project.archive_requested", "project", project_id)
    _notify_project_members(
        db, project, "project.archive_requested",
        "Project archival requested",
        f"{user.full_name} requested archival of “{project.title}”.",
        dedupe_suffix=project.archive_requested_at.isoformat(),
        roles=("supervisor",),
    )

    _commit(db)
    db.refresh(project)
    return access


def archive_project(db: Session, user: User, project_id: UUID) -> ProjectAccess:
    access = get_project_access(db, user, project_id, lock=True)
    require(access.can_archive, "You cannot archive this project.")

    project = access.project
    project.status = "archived"
    project.archived_by = user.id
    project.archived_at = _now()

    record_audit(db, user.id, "project.archived", "project", project_id)
    _commit(db)
    db.refresh(project)
    return access


def unarchive_project(db: Session, user: User, project_id: UUID) -> ProjectAccess:
    access = get_project_access(db, user, project_id, lock=True)
    require(access.can_unarchive, "You cannot restore this archived project.")

    project = access.project
    project.status = "active"
    project.archived_by = None
    project.archived_at = None
    project.archive_requested_by = None
    project.archive_requested_at = None
    project.archive_request_reason = None

    record_audit(db, user.id, "project.unarchived", "project", project_id)
    _commit(db)
    db.refresh(project)
    return access


def soft_delete_project(db: Session, user: User, project_id: UUID) -> ProjectAccess:
    access = get_project_access(db, user, project_id, lock=True)
    require(access.can_soft_delete, "You cannot delete this project.")

    project = access.project
    project.status = "deleted"
    project.deleted_by = user.id
    project.deleted_at = _now()

    record_audit(db, user.id, "project.deleted", "project", project_id)
    _commit(db)
    db.refresh(project)
    return access


def restore_project(db: Session, user: User, project_id: UUID) -> ProjectAccess:
    access = get_project_access(db, user, project_id, lock=True)
    require(access.can_restore, "Only administrators can restore deleted projects.")

    project = access.project
    project.status = "archived" if project.archived_at else "active"
    project.deleted_by = None
    project.deleted_at = None

    record_audit(db, user.id, "project.restored", "project", project_id, {"status": project.status})
    _commit(db)
    db.refresh(project)
    return access


def purge_project(db: Session, user: User, project_id: UUID) -> None:
    """Permanently delete a soft-deleted project after the retention window.

    Project-specific rows (membership, tasks, handbook entries and paper or
    conference associations) cascade. Shared research papers and
    conference records are kept.
    """

    access = get_project_access(db, user, project_id, lock=True)
    require(access.is_admin, "Only administrators can permanently delete projects.")

    project = access.project
    if project.status != "deleted":
        raise ConflictError("Only deleted projects can be permanently deleted.")

    eligible = purge_eligible_at(project)
    if eligible and eligible > _now():
        raise ConflictError(
            "Deleted projects are recoverable for "
            f"{settings.PROJECT_DELETE_RETENTION_DAYS} days and can be "
            f"permanently deleted after {eligible.date().isoformat()}."
        )

    record_audit(db, user.id, "project.purged", "project", project_id, {"title": project.title})
    db.execute(delete(Project).where(Project.id == project_id))
    _commit(db)


# --- Membership ----------------------------------------------------------------


def list_members(db: Session, user: User, project_id: UUID, include_removed: bool = False):
    access = get_project_access(db, user, project_id)

    statement = (
        select(ProjectMember)
        .options(selectinload(ProjectMember.user))
        .where(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.joined_at)
    )
    if not (include_removed and access.is_manager):
        statement = statement.where(ProjectMember.membership_status == "active")

    return db.scalars(statement).all()


def _validate_member_role(target: User, membership_role: str) -> None:
    roles = target.role_names

    if target.account_status != "approved":
        raise BadRequestError("Only approved users can join projects.")

    if membership_role == "supervisor" and PROFESSOR not in roles:
        raise BadRequestError("Only professors can supervise projects.")

    if membership_role == "guest" and roles != {GUEST}:
        raise BadRequestError("Guest access is only for users with the Guest role.")

    if membership_role != "guest" and roles == {GUEST}:
        raise BadRequestError("Guest users can only receive read-only guest access.")


def add_member(
    db: Session, user: User, project_id: UUID, member_user_id: UUID, membership_role: str
) -> ProjectMember:
    access = get_project_access(db, user, project_id, lock=True)
    require(access.can_manage_members, "You cannot manage this project's members.")

    target = db.get(User, member_user_id)
    if not target:
        raise NotFoundError("User not found.")

    _validate_member_role(target, membership_role)

    membership = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == member_user_id,
        )
    )

    if membership and membership.membership_status == "active":
        raise ConflictError("The user is already a project member.")

    if membership:
        membership.membership_status = "active"
        membership.membership_role = membership_role
        membership.removed_at = None
        membership.added_by = user.id
        membership.joined_at = _now()
    else:
        membership = ProjectMember(
            project_id=project_id,
            user_id=member_user_id,
            membership_role=membership_role,
            added_by=user.id,
        )
        db.add(membership)

    record_audit(
        db, user.id, "project.member_added", "project", project_id,
        {"member_id": member_user_id, "membership_role": membership_role},
    )
    enqueue_notification(
        db,
        recipient_id=member_user_id,
        category="projects",
        event_type="project.member_added",
        title="Added to a project",
        body=f"You were added to “{access.project.title}” as {membership_role}.",
        entity_type="project",
        entity_id=project_id,
        dedupe_key=f"project.member_added:{project_id}:{member_user_id}:{_now().isoformat()}",
    )

    _commit(db)
    db.refresh(membership)
    return membership


def _get_active_membership(db: Session, project_id: UUID, member_user_id: UUID) -> ProjectMember:
    membership = db.scalar(
        select(ProjectMember)
        .where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == member_user_id,
            ProjectMember.membership_status == "active",
        )
        .with_for_update()
    )
    if not membership:
        raise NotFoundError("Project member not found.")
    return membership


def change_member_role(
    db: Session, user: User, project_id: UUID, member_user_id: UUID, membership_role: str
) -> ProjectMember:
    access = get_project_access(db, user, project_id, lock=True)
    require(access.can_manage_members, "You cannot manage this project's members.")

    membership = _get_active_membership(db, project_id, member_user_id)
    if membership.membership_role == "owner":
        raise ConflictError("Use ownership transfer to change the owner.")

    _validate_member_role(membership.user, membership_role)

    previous = membership.membership_role
    membership.membership_role = membership_role

    record_audit(
        db, user.id, "project.member_role_changed", "project", project_id,
        {"member_id": member_user_id, "from": previous, "to": membership_role},
    )
    _commit(db)
    db.refresh(membership)
    return membership


def remove_member(db: Session, user: User, project_id: UUID, member_user_id: UUID) -> None:
    access = get_project_access(db, user, project_id, lock=True)
    require(access.can_manage_members, "You cannot manage this project's members.")

    membership = _get_active_membership(db, project_id, member_user_id)
    if membership.membership_role == "owner":
        raise ConflictError(
            "The project owner cannot be removed. An administrator must transfer ownership first."
        )

    membership.membership_status = "removed"
    membership.removed_at = _now()

    record_audit(
        db, user.id, "project.member_removed", "project", project_id,
        {"member_id": member_user_id},
    )
    _commit(db)


def transfer_ownership(db: Session, user: User, project_id: UUID, new_owner_id: UUID) -> ProjectAccess:
    access = get_project_access(db, user, project_id, lock=True)
    require(access.is_admin, "Only administrators can transfer project ownership.")

    project = access.project
    if project.owner_id == new_owner_id:
        raise ConflictError("The user already owns this project.")

    new_owner = db.get(User, new_owner_id)
    if not new_owner or new_owner.account_status != "approved":
        raise BadRequestError("The new owner must be an approved user.")
    if new_owner.role_names == {GUEST}:
        raise BadRequestError("Guest users cannot own projects.")

    previous_owner_id = project.owner_id
    old_membership = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == previous_owner_id,
        )
    )
    if old_membership:
        previous_user = db.get(User, previous_owner_id)
        old_membership.membership_role = (
            "supervisor" if PROFESSOR in previous_user.role_names else "member"
        )

    new_membership = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == new_owner_id,
        )
    )
    if new_membership:
        new_membership.membership_role = "owner"
        new_membership.membership_status = "active"
        new_membership.removed_at = None
    else:
        db.add(
            ProjectMember(
                project_id=project_id,
                user_id=new_owner_id,
                membership_role="owner",
                added_by=user.id,
            )
        )

    project.owner_id = new_owner_id

    record_audit(
        db, user.id, "project.ownership_transferred", "project", project_id,
        {"from": previous_owner_id, "to": new_owner_id},
    )
    _commit(db)
    db.refresh(project)
    return get_project_access(db, user, project_id)
