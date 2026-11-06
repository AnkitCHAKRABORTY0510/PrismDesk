from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import has_capability
from app.models.handbook import (
    DailySummary,
    DailySummaryVersion,
    HandbookComment,
    HandbookEntry,
    HandbookEntryVersion,
)
from app.models.project import Project
from app.models.user import User
from app.schemas.admin import user_summary
from app.schemas.common import PageParams, paginate
from app.schemas.handbook import (
    CommentResponse,
    EntryCreate,
    EntryResponse,
    EntryUpdate,
    SummaryCreate,
    SummaryUpdate,
)
from app.services.audit_service import record_audit
from app.services.notification_service import enqueue_notification
from app.services.project_access import (
    ProjectAccess,
    get_project_access,
    managed_project_ids,
    require,
)

ENTRY_FIELDS = ("work_completed", "research_progress", "problems", "next_steps", "references")
SUMMARY_FIELDS = ("summary", "challenges", "plan_next")


def _commit(db: Session):
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _check_date(entry_date: date) -> None:
    # Allow "tomorrow" to absorb timezone differences between the lab
    # workstation and the browser.
    if entry_date > datetime.now(timezone.utc).date() + timedelta(days=1):
        raise BadRequestError("Entries cannot be dated in the future.")


def _entry_snapshot(entry: HandbookEntry) -> dict:
    return {field: getattr(entry, field) for field in ENTRY_FIELDS}


# --- Access --------------------------------------------------------------------------


def _entry_access(db: Session, user: User, entry_id: UUID) -> tuple[HandbookEntry, ProjectAccess | None]:
    entry = db.get(HandbookEntry, entry_id)
    if not entry:
        raise NotFoundError("Handbook entry not found.")

    if entry.student_id == user.id:
        try:
            return entry, get_project_access(db, user, entry.project_id)
        except NotFoundError:
            # Removed from the project: the student keeps read access to
            # their own history.
            return entry, None

    try:
        access = get_project_access(db, user, entry.project_id)
    except NotFoundError:
        raise NotFoundError("Handbook entry not found.")

    if not access.is_manager:
        raise NotFoundError("Handbook entry not found.")

    return entry, access


def _can_edit(entry: HandbookEntry, user: User, access: ProjectAccess | None) -> bool:
    return entry.student_id == user.id and bool(access and access.is_active)


def _can_comment(access: ProjectAccess | None) -> bool:
    return bool(access and access.is_manager and access.is_active)


# --- Entries -------------------------------------------------------------------------


def create_entry(db: Session, user: User, data: EntryCreate) -> HandbookEntry:
    if not has_capability(user.role_names, "handbook.write"):
        raise ForbiddenError("Only students write handbook entries.")

    access = get_project_access(db, user, data.project_id)
    require(
        access.is_active and access.role in ("owner", "member"),
        "You can only write entries for active projects you are a member of.",
    )
    _check_date(data.entry_date)

    entry = HandbookEntry(
        student_id=user.id,
        project_id=data.project_id,
        entry_date=data.entry_date,
        work_completed=data.work_completed.strip(),
        research_progress=data.research_progress.strip(),
        problems=data.problems.strip(),
        next_steps=data.next_steps.strip(),
        references=[str(url) for url in data.references],
        version=1,
    )
    db.add(entry)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError("You already have an entry for this project on this date. Edit it instead.")

    db.add(
        HandbookEntryVersion(entry_id=entry.id, version=1, snapshot=_entry_snapshot(entry), edited_by=user.id)
    )
    _commit(db)
    db.refresh(entry)
    return entry


def update_entry(db: Session, user: User, entry_id: UUID, data: EntryUpdate) -> HandbookEntry:
    entry, access = _entry_access(db, user, entry_id)
    if entry.student_id != user.id:
        # Professors and administrators comment; they never edit.
        raise ForbiddenError("Only the author can edit a handbook entry.")
    require(_can_edit(entry, user, access), "Entries of archived projects are read-only.")

    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    if not changes:
        return entry

    for field, value in changes.items():
        if field == "references":
            value = [str(url) for url in data.references]
        else:
            value = value.strip()
        setattr(entry, field, value)

    if not any(getattr(entry, f).strip() for f in ENTRY_FIELDS if f != "references"):
        db.rollback()
        raise BadRequestError("An entry cannot be emptied.")

    entry.version += 1
    db.add(
        HandbookEntryVersion(
            entry_id=entry.id, version=entry.version, snapshot=_entry_snapshot(entry), edited_by=user.id
        )
    )
    _commit(db)
    db.refresh(entry)
    return entry


def get_entry(db: Session, user: User, entry_id: UUID):
    return _entry_access(db, user, entry_id)


def list_entries(
    db: Session,
    user: User,
    params: PageParams,
    project_id: UUID | None = None,
    student_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    """Own entries plus entries of projects the user supervises."""

    statement = (
        select(HandbookEntry)
        .options(selectinload(HandbookEntry.student))
        .join(Project, Project.id == HandbookEntry.project_id)
        .where(
            Project.status != "deleted",
            or_(
                HandbookEntry.student_id == user.id,
                HandbookEntry.project_id.in_(managed_project_ids(user)),
            ),
        )
        .order_by(HandbookEntry.entry_date.desc(), HandbookEntry.created_at.desc())
    )

    if project_id:
        get_project_access(db, user, project_id)
        statement = statement.where(HandbookEntry.project_id == project_id)
    if student_id:
        statement = statement.where(HandbookEntry.student_id == student_id)
    if date_from:
        statement = statement.where(HandbookEntry.entry_date >= date_from)
    if date_to:
        statement = statement.where(HandbookEntry.entry_date <= date_to)

    return paginate(db, statement, params)


def entry_versions(db: Session, user: User, entry_id: UUID) -> list[HandbookEntryVersion]:
    _entry_access(db, user, entry_id)
    return list(
        db.scalars(
            select(HandbookEntryVersion)
            .where(HandbookEntryVersion.entry_id == entry_id)
            .order_by(HandbookEntryVersion.version.desc())
        ).all()
    )


def _comment_tree(comments: list[HandbookComment]) -> list[CommentResponse]:
    nodes = {
        c.id: CommentResponse(
            id=c.id,
            entry_id=c.entry_id,
            parent_id=c.parent_id,
            author=user_summary(c.author) if c.author else None,
            body=c.body,
            created_at=c.created_at,
        )
        for c in comments
    }
    roots = []
    for comment in comments:
        node = nodes[comment.id]
        if comment.parent_id and comment.parent_id in nodes:
            nodes[comment.parent_id].replies.append(node)
        else:
            roots.append(node)
    return roots


def entry_responses(db: Session, user: User, entries: list[HandbookEntry], with_comments: bool = False):
    if not entries:
        return []

    ids = [entry.id for entry in entries]
    titles = dict(
        db.execute(
            select(Project.id, Project.title).where(Project.id.in_({e.project_id for e in entries}))
        ).all()
    )
    counts = dict(
        db.execute(
            select(HandbookComment.entry_id, func.count())
            .where(HandbookComment.entry_id.in_(ids))
            .group_by(HandbookComment.entry_id)
        ).all()
    )
    managed = set(db.scalars(managed_project_ids(user)).all())

    comments_by_entry: dict[UUID, list[HandbookComment]] = {}
    if with_comments:
        for comment in db.scalars(
            select(HandbookComment)
            .options(selectinload(HandbookComment.author))
            .where(HandbookComment.entry_id.in_(ids))
            .order_by(HandbookComment.created_at)
        ).all():
            comments_by_entry.setdefault(comment.entry_id, []).append(comment)

    statuses = dict(
        db.execute(select(Project.id, Project.status).where(Project.id.in_(titles.keys()))).all()
    )

    responses = []
    for entry in entries:
        active = statuses.get(entry.project_id) == "active"
        responses.append(
            EntryResponse(
                id=entry.id,
                student=user_summary(entry.student),
                project_id=entry.project_id,
                project_title=titles.get(entry.project_id),
                entry_date=entry.entry_date,
                work_completed=entry.work_completed,
                research_progress=entry.research_progress,
                problems=entry.problems,
                next_steps=entry.next_steps,
                references=entry.references,
                version=entry.version,
                created_at=entry.created_at,
                updated_at=entry.updated_at,
                comment_count=counts.get(entry.id, 0),
                comments=_comment_tree(comments_by_entry.get(entry.id, [])),
                can_edit=entry.student_id == user.id and active,
                can_comment=active and (entry.project_id in managed or entry.student_id == user.id),
            )
        )
    return responses


def add_comment(db: Session, user: User, entry_id: UUID, body: str, parent_id: UUID | None) -> HandbookComment:
    entry, access = _entry_access(db, user, entry_id)
    if not (access and access.is_active):
        raise ForbiddenError("Entries of archived projects are read-only.")

    parent = None
    if parent_id:
        parent = db.get(HandbookComment, parent_id)
        if not parent or parent.entry_id != entry.id:
            raise NotFoundError("Comment not found.")
        if parent.parent_id is not None:
            raise BadRequestError("Replies can only be added to top-level comments.")
        # Replies come from the entry's author or a supervisor.
        require(entry.student_id == user.id or access.is_manager, "You cannot reply here.")
    else:
        require(_can_comment(access), "Only project supervisors can comment on entries.")

    comment = HandbookComment(entry_id=entry.id, parent_id=parent_id, author_id=user.id, body=body.strip())
    db.add(comment)
    db.flush()

    record_audit(
        db, user.id, "handbook.reply_added" if parent else "handbook.comment_added", "handbook_entry", entry.id,
        {"comment_id": comment.id, "project_id": entry.project_id},
    )

    recipients = set()
    if parent is None:
        recipients.add(entry.student_id)
    else:
        if parent.author_id:
            recipients.add(parent.author_id)
        recipients.add(entry.student_id)
    recipients.discard(user.id)

    for recipient_id in recipients:
        enqueue_notification(
            db,
            recipient_id=recipient_id,
            category="handbook",
            event_type="handbook.comment_added",
            title="New handbook comment",
            body=f"{user.full_name} commented on the {entry.entry_date.isoformat()} handbook entry.",
            entity_type="handbook_entry",
            entity_id=entry.id,
            dedupe_key=f"handbook.comment:{comment.id}:{recipient_id}",
        )

    _commit(db)
    db.refresh(comment)
    return comment


def progress_by_date(
    db: Session,
    user: User,
    project_id: UUID | None,
    date_from: date,
    date_to: date,
):
    statement = (
        select(
            HandbookEntry.entry_date,
            func.count(HandbookEntry.id),
            func.count(func.distinct(HandbookEntry.student_id)),
        )
        .join(Project, Project.id == HandbookEntry.project_id)
        .where(
            Project.status != "deleted",
            HandbookEntry.entry_date.between(date_from, date_to),
            or_(
                HandbookEntry.student_id == user.id,
                HandbookEntry.project_id.in_(managed_project_ids(user)),
            ),
        )
        .group_by(HandbookEntry.entry_date)
        .order_by(HandbookEntry.entry_date)
    )
    if project_id:
        get_project_access(db, user, project_id)
        statement = statement.where(HandbookEntry.project_id == project_id)
    return db.execute(statement).all()


# --- Overall daily summaries (private) --------------------------------------------


def _own_summary(db: Session, user: User, summary_id: UUID) -> DailySummary:
    summary = db.scalar(
        select(DailySummary).where(DailySummary.id == summary_id, DailySummary.student_id == user.id)
    )
    if not summary:
        raise NotFoundError("Daily summary not found.")
    return summary


def _summary_snapshot(summary: DailySummary) -> dict:
    return {field: getattr(summary, field) for field in SUMMARY_FIELDS}


def create_summary(db: Session, user: User, data: SummaryCreate) -> DailySummary:
    if not has_capability(user.role_names, "handbook.write"):
        raise ForbiddenError("Only students write daily summaries.")
    _check_date(data.entry_date)

    summary = DailySummary(
        student_id=user.id,
        entry_date=data.entry_date,
        summary=data.summary.strip(),
        challenges=data.challenges.strip(),
        plan_next=data.plan_next.strip(),
    )
    db.add(summary)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError("You already have a summary for this date. Edit it instead.")

    db.add(DailySummaryVersion(summary_id=summary.id, version=1, snapshot=_summary_snapshot(summary)))
    _commit(db)
    db.refresh(summary)
    return summary


def update_summary(db: Session, user: User, summary_id: UUID, data: SummaryUpdate) -> DailySummary:
    summary = _own_summary(db, user, summary_id)
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    if not changes:
        return summary

    for field, value in changes.items():
        setattr(summary, field, value.strip())
    if not summary.summary:
        db.rollback()
        raise BadRequestError("The summary cannot be empty.")

    summary.version += 1
    db.add(DailySummaryVersion(summary_id=summary.id, version=summary.version, snapshot=_summary_snapshot(summary)))
    _commit(db)
    db.refresh(summary)
    return summary


def list_summaries(db: Session, user: User, params: PageParams, date_from: date | None, date_to: date | None):
    statement = (
        select(DailySummary)
        .where(DailySummary.student_id == user.id)
        .order_by(DailySummary.entry_date.desc())
    )
    if date_from:
        statement = statement.where(DailySummary.entry_date >= date_from)
    if date_to:
        statement = statement.where(DailySummary.entry_date <= date_to)
    return paginate(db, statement, params)


def summary_versions(db: Session, user: User, summary_id: UUID) -> list[DailySummaryVersion]:
    _own_summary(db, user, summary_id)
    return list(
        db.scalars(
            select(DailySummaryVersion)
            .where(DailySummaryVersion.summary_id == summary_id)
            .order_by(DailySummaryVersion.version.desc())
        ).all()
    )
