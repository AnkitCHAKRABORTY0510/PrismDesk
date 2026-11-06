from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import ADMINISTRATOR, PROFESSOR, has_capability
from app.models.conference import Conference, ProjectConference
from app.models.project import Project
from app.models.user import User
from app.schemas.common import PageParams, paginate
from app.schemas.conference import (
    ConferenceCreate,
    ConferenceProjectLink,
    ConferenceResponse,
    ConferenceUpdate,
)
from app.services.audit_service import record_audit
from app.services.project_access import get_project_access, managed_project_ids, require, visible_project_ids


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _commit(db: Session):
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _visibility_filter(user: User):
    if has_capability(user.role_names, "conferences.view"):
        return None
    # Guests only see conferences linked to projects they can read.
    return Conference.id.in_(
        select(ProjectConference.conference_id).where(
            ProjectConference.project_id.in_(visible_project_ids(user)),
            ProjectConference.status == "active",
        )
    )


def can_edit_conference(user: User, conference: Conference) -> bool:
    roles = user.role_names
    return ADMINISTRATOR in roles or PROFESSOR in roles or conference.added_by == user.id


def get_conference(db: Session, user: User, conference_id: UUID) -> Conference:
    conference = db.get(Conference, conference_id)
    if not conference:
        raise NotFoundError("Conference not found.")
    condition = _visibility_filter(user)
    if condition is not None and not db.scalar(
        select(Conference.id).where(Conference.id == conference_id, condition)
    ):
        raise NotFoundError("Conference not found.")
    return conference


def conference_responses(db: Session, user: User, conferences: list[Conference]) -> list[ConferenceResponse]:
    if not conferences:
        return []

    now = _now()
    managed = set(db.scalars(managed_project_ids(user)).all())

    links: dict[UUID, list[ConferenceProjectLink]] = {}
    for link, title in db.execute(
        select(ProjectConference, Project.title)
        .join(Project, Project.id == ProjectConference.project_id)
        .where(
            ProjectConference.conference_id.in_([c.id for c in conferences]),
            Project.id.in_(visible_project_ids(user)),
        )
        .order_by(Project.title)
    ).all():
        links.setdefault(link.conference_id, []).append(
            ConferenceProjectLink(
                project_id=link.project_id,
                project_title=title,
                status=link.status,
                added_at=link.added_at,
                can_manage=link.project_id in managed or link.added_by == user.id,
            )
        )

    return [
        ConferenceResponse(
            id=c.id,
            name=c.name,
            acronym=c.acronym,
            website_url=c.website_url,
            cfp_url=c.cfp_url,
            submission_deadline=c.submission_deadline,
            important_dates=c.important_dates,
            location=c.location,
            notes=c.notes,
            added_by=c.added_by,
            created_at=c.created_at,
            updated_at=c.updated_at,
            is_overdue=c.submission_deadline < now,
            seconds_remaining=int((c.submission_deadline - now).total_seconds()),
            projects=links.get(c.id, []),
            can_edit=can_edit_conference(user, c),
        )
        for c in conferences
    ]


def list_conferences(
    db: Session,
    user: User,
    params: PageParams,
    search: str | None = None,
    project_id: UUID | None = None,
    deadline_from: datetime | None = None,
    deadline_to: datetime | None = None,
    timing: str | None = None,
    include_archived_links: bool = False,
) -> tuple[list[Conference], int]:
    statement = select(Conference)

    condition = _visibility_filter(user)
    if condition is not None:
        statement = statement.where(condition)

    if search and search.strip():
        term = f"%{search.strip()}%"
        statement = statement.where(
            or_(Conference.name.ilike(term), Conference.acronym.ilike(term), Conference.location.ilike(term))
        )

    if project_id:
        get_project_access(db, user, project_id)
        links = select(ProjectConference.conference_id).where(ProjectConference.project_id == project_id)
        if not include_archived_links:
            links = links.where(ProjectConference.status == "active")
        statement = statement.where(Conference.id.in_(links))

    if deadline_from:
        statement = statement.where(Conference.submission_deadline >= deadline_from)
    if deadline_to:
        statement = statement.where(Conference.submission_deadline <= deadline_to)

    if timing == "upcoming":
        statement = statement.where(Conference.submission_deadline >= func.now()).order_by(
            Conference.submission_deadline.asc()
        )
    elif timing == "overdue":
        statement = statement.where(Conference.submission_deadline < func.now()).order_by(
            Conference.submission_deadline.desc()
        )
    else:
        # Upcoming deadlines first (soonest first), then past ones.
        statement = statement.order_by(
            (Conference.submission_deadline < func.now()).asc(),
            Conference.submission_deadline.asc(),
        )

    return paginate(db, statement, params)


def _link(db: Session, user: User, conference_id: UUID, project_id: UUID) -> bool:
    access = get_project_access(db, user, project_id)
    require(access.can_contribute, "You cannot add conferences to this project.")

    existing = db.get(ProjectConference, (project_id, conference_id))
    if existing:
        if existing.status == "active":
            return False
        existing.status = "active"
        existing.archived_at = None
        existing.archived_by = None
    else:
        db.execute(
            insert(ProjectConference)
            .values(project_id=project_id, conference_id=conference_id, added_by=user.id)
            .on_conflict_do_nothing()
        )

    record_audit(db, user.id, "conference.linked", "conference", conference_id, {"project_id": project_id})
    return True


def create_conference(db: Session, user: User, data: ConferenceCreate) -> tuple[Conference, bool]:
    if not has_capability(user.role_names, "conferences.create"):
        raise ForbiddenError("You cannot add conferences.")

    duplicate = db.scalar(
        select(Conference).where(
            func.lower(Conference.name) == data.name.lower(),
            Conference.submission_deadline == data.submission_deadline,
        )
    )
    if duplicate:
        if not data.project_id:
            raise ConflictError("This conference deadline already exists. Link it to your project instead.")
        _link(db, user, duplicate.id, data.project_id)
        _commit(db)
        return duplicate, True

    conference = Conference(
        name=data.name,
        acronym=(data.acronym or "").strip() or None,
        website_url=str(data.website_url) if data.website_url else None,
        cfp_url=str(data.cfp_url) if data.cfp_url else None,
        submission_deadline=data.submission_deadline,
        important_dates=[d.model_dump(mode="json") for d in data.important_dates],
        location=(data.location or "").strip() or None,
        notes=data.notes.strip(),
        added_by=user.id,
    )
    db.add(conference)
    db.flush()
    record_audit(db, user.id, "conference.created", "conference", conference.id, {"name": conference.name})

    if data.project_id:
        _link(db, user, conference.id, data.project_id)

    _commit(db)
    db.refresh(conference)
    return conference, False


def update_conference(db: Session, user: User, conference_id: UUID, data: ConferenceUpdate) -> Conference:
    conference = get_conference(db, user, conference_id)
    require(can_edit_conference(user, conference), "You cannot edit this conference.")

    changes = data.model_dump(exclude_unset=True, mode="json")
    for field, value in changes.items():
        if field == "submission_deadline":
            value = data.submission_deadline
            if value is None:
                continue
        if field == "name" and value is None:
            continue
        if field == "important_dates" and value is None:
            value = []
        if field == "notes" and value is None:
            value = ""
        setattr(conference, field, value)

    if changes:
        record_audit(db, user.id, "conference.updated", "conference", conference.id, {"fields": sorted(changes)})

    try:
        _commit(db)
    except Exception as error:
        if "uq_conferences_name_deadline" in str(error):
            raise ConflictError("Another conference with this name and deadline exists.")
        raise
    db.refresh(conference)
    return conference


def delete_conference(db: Session, user: User, conference_id: UUID) -> None:
    conference = get_conference(db, user, conference_id)
    active_links = db.scalar(
        select(func.count()).select_from(ProjectConference).where(
            ProjectConference.conference_id == conference_id, ProjectConference.status == "active"
        )
    )
    is_admin = ADMINISTRATOR in user.role_names
    require(
        is_admin or (conference.added_by == user.id and not active_links),
        "Only administrators can delete conferences that projects still use.",
    )
    record_audit(db, user.id, "conference.deleted", "conference", conference_id, {"name": conference.name})
    db.delete(conference)
    _commit(db)


def link_conference(db: Session, user: User, conference_id: UUID, project_id: UUID) -> Conference:
    conference = get_conference(db, user, conference_id)
    if not _link(db, user, conference.id, project_id):
        raise ConflictError("The conference is already linked to this project.")
    _commit(db)
    return conference


def _load_link(db: Session, user: User, conference_id: UUID, project_id: UUID):
    access = get_project_access(db, user, project_id)
    link = db.get(ProjectConference, (project_id, conference_id))
    if not link:
        raise NotFoundError("The conference is not linked to this project.")
    require(
        access.is_active and (access.is_manager or (access.can_contribute and link.added_by == user.id)),
        "You cannot change this project's conference list.",
    )
    return link


def archive_link(db: Session, user: User, conference_id: UUID, project_id: UUID) -> None:
    link = _load_link(db, user, conference_id, project_id)
    if link.status == "archived":
        raise ConflictError("The association is already archived.")
    link.status = "archived"
    link.archived_at = _now()
    link.archived_by = user.id
    record_audit(db, user.id, "conference.link_archived", "conference", conference_id, {"project_id": project_id})
    _commit(db)


def unlink_conference(db: Session, user: User, conference_id: UUID, project_id: UUID) -> None:
    link = _load_link(db, user, conference_id, project_id)
    db.delete(link)
    record_audit(db, user.id, "conference.unlinked", "conference", conference_id, {"project_id": project_id})
    _commit(db)
