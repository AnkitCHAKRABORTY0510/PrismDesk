"""Each user's personal journal list (with optional special-issue deadline)."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import case, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import has_capability
from app.models.journal import Journal
from app.models.project import Project
from app.models.user import User
from app.schemas.common import PageParams, paginate
from app.schemas.journal import JournalCreate, JournalResponse, JournalUpdate
from app.services.audit_service import record_audit
from app.services.journal_catalog import normalize_issn, special_issue_links, title_key
from app.services.project_access import get_project_access, require


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _commit(db: Session):
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if "uq_journals_owner" in str(error):
            raise ConflictError("This journal is already in your list.")
        raise
    except Exception:
        db.rollback()
        raise


def require_create(user: User) -> None:
    if not has_capability(user.role_names, "journals.create"):
        raise ForbiddenError("You cannot add journals.")


def _check_project(db: Session, user: User, project_id: UUID | None) -> None:
    if project_id:
        access = get_project_access(db, user, project_id)
        require(access.can_contribute, "You cannot target journals for this project.")


def journal_responses(db: Session, journals: list[Journal]) -> list[JournalResponse]:
    now = _now()
    project_ids = {j.project_id for j in journals if j.project_id}
    titles = (
        dict(db.execute(select(Project.id, Project.title).where(Project.id.in_(project_ids))).all())
        if project_ids
        else {}
    )
    result = []
    for j in journals:
        remaining = int((j.submission_deadline - now).total_seconds()) if j.submission_deadline else None
        result.append(
            JournalResponse(
                id=j.id,
                title=j.title,
                issn=j.issn,
                publisher=j.publisher,
                homepage_url=j.homepage_url,
                sjr_quartile=j.sjr_quartile,
                sjr=j.sjr,
                h_index=j.h_index,
                subject_areas=j.subject_areas or [],
                is_open_access=j.is_open_access,
                notes=j.notes,
                special_issue_title=j.special_issue_title,
                submission_deadline=j.submission_deadline,
                project_id=j.project_id,
                project_title=titles.get(j.project_id),
                created_at=j.created_at,
                updated_at=j.updated_at,
                is_overdue=remaining is not None and remaining < 0,
                seconds_remaining=remaining,
                **special_issue_links(j.title),
            )
        )
    return result


def get_journal(db: Session, user: User, journal_id: UUID) -> Journal:
    journal = db.get(Journal, journal_id)
    # Lists are private: other users' journals simply do not exist.
    if not journal or journal.owner_id != user.id:
        raise NotFoundError("Journal not found.")
    return journal


def list_journals(
    db: Session,
    user: User,
    params: PageParams,
    search: str | None = None,
    deadline: str | None = None,
    project_id: UUID | None = None,
) -> tuple[list[Journal], int]:
    statement = select(Journal).where(Journal.owner_id == user.id)
    if search and search.strip():
        term = f"%{search.strip()}%"
        statement = statement.where(
            or_(Journal.title.ilike(term), Journal.publisher.ilike(term), Journal.issn.ilike(term),
                Journal.special_issue_title.ilike(term))
        )
    if deadline == "special":
        statement = statement.where(Journal.submission_deadline.is_not(None))
    elif deadline == "rolling":
        statement = statement.where(Journal.submission_deadline.is_(None))
    if project_id:
        statement = statement.where(Journal.project_id == project_id)

    now = _now()
    # Upcoming special-issue deadlines first (soonest first), then rolling, then passed.
    bucket = case(
        (Journal.submission_deadline >= now, 0),
        (Journal.submission_deadline.is_(None), 1),
        else_=2,
    )
    statement = statement.order_by(bucket, Journal.submission_deadline.asc(), Journal.title.asc())
    return paginate(db, statement, params)


def find_existing(db: Session, user: User, issns: list[str], title: str) -> Journal | None:
    conditions = [Journal.title_key == title_key(title)]
    normalized = [i for i in (normalize_issn(x) for x in issns) if i]
    if normalized:
        conditions.append(Journal.issn.in_(normalized))
    return db.scalar(select(Journal).where(Journal.owner_id == user.id, or_(*conditions)).limit(1))


def catalog_matches(db: Session, user: User, items: list[dict]) -> dict[int, UUID]:
    """Index of catalog items (by position) already on the user's list."""
    issns = {i for item in items for i in item["issns"]}
    keys = {title_key(item["title"]) for item in items}
    rows = db.execute(
        select(Journal.id, Journal.issn, Journal.title_key).where(
            Journal.owner_id == user.id,
            or_(Journal.issn.in_(issns or {""}), Journal.title_key.in_(keys or {""})),
        )
    ).all()
    by_issn = {r.issn: r.id for r in rows if r.issn}
    by_key = {r.title_key: r.id for r in rows}
    result = {}
    for index, item in enumerate(items):
        match = next((by_issn[i] for i in item["issns"] if i in by_issn), None) or by_key.get(title_key(item["title"]))
        if match:
            result[index] = match
    return result


def create_journal(db: Session, user: User, data: JournalCreate) -> Journal:
    require_create(user)
    _check_project(db, user, data.project_id)
    if find_existing(db, user, [data.issn] if data.issn else [], data.title):
        raise ConflictError("This journal is already in your list.")

    journal = Journal(
        owner_id=user.id,
        title=data.title,
        title_key=title_key(data.title),
        issn=data.issn,
        publisher=(data.publisher or "").strip() or None,
        homepage_url=str(data.homepage_url) if data.homepage_url else None,
        sjr_quartile=data.sjr_quartile,
        sjr=data.sjr,
        h_index=data.h_index,
        subject_areas=[a.strip()[:100] for a in data.subject_areas if a.strip()],
        is_open_access=data.is_open_access,
        notes=data.notes.strip(),
        special_issue_title=(data.special_issue_title or "").strip() or None,
        submission_deadline=data.submission_deadline,
        project_id=data.project_id,
    )
    db.add(journal)
    db.flush()
    record_audit(db, user.id, "journal.created", "journal", journal.id, {"title": journal.title})
    _commit(db)
    db.refresh(journal)
    return journal


def update_journal(db: Session, user: User, journal_id: UUID, data: JournalUpdate) -> Journal:
    journal = get_journal(db, user, journal_id)
    changes = data.model_dump(exclude_unset=True)
    if "project_id" in changes:
        _check_project(db, user, changes["project_id"])
    for name, value in changes.items():
        if name in {"title", "subject_areas", "is_open_access", "notes"} and value is None:
            continue
        if name == "homepage_url" and value is not None:
            value = str(value)
        if name in {"publisher", "special_issue_title"} and value is not None:
            value = value.strip() or None
        if name == "title":
            value = value.strip()
            journal.title_key = title_key(value)
        setattr(journal, name, value)
    if changes:
        record_audit(db, user.id, "journal.updated", "journal", journal.id, {"fields": sorted(changes)})
    _commit(db)
    db.refresh(journal)
    return journal


def delete_journal(db: Session, user: User, journal_id: UUID) -> None:
    journal = get_journal(db, user, journal_id)
    record_audit(db, user.id, "journal.deleted", "journal", journal.id, {"title": journal.title})
    db.delete(journal)
    _commit(db)


def add_from_catalog(db: Session, user: User, item: dict, project_id: UUID | None) -> tuple[Journal, bool]:
    """Add a catalog journal; returns (journal, already_existed)."""
    require_create(user)
    existing = find_existing(db, user, item["issns"], item["title"])
    if existing:
        if project_id and existing.project_id != project_id:
            _check_project(db, user, project_id)
            existing.project_id = project_id
            _commit(db)
        return existing, True

    notes = []
    if item.get("categories"):
        notes.append(
            "Categories: "
            + "; ".join(f"{c['name']} ({c['quartile']})" if c.get("quartile") else c["name"] for c in item["categories"][:10])
        )
    if item.get("apc_usd"):
        notes.append(f"APC: US${item['apc_usd']}")
    if item.get("is_in_doaj"):
        notes.append("Listed in DOAJ.")
    sources = ["OpenAlex"] if item.get("enriched") else []
    if item.get("sjr_quartile") or item.get("sjr"):
        sources.insert(0, "SCImago Journal Rank")
    if sources:
        notes.append(f"Imported from {' and '.join(sources)}.")

    data = JournalCreate(
        title=item["title"],
        issn=item["issn"],
        publisher=item.get("publisher"),
        homepage_url=item.get("homepage_url"),
        sjr_quartile=item.get("sjr_quartile"),
        sjr=item.get("sjr"),
        h_index=item.get("h_index"),
        subject_areas=item.get("areas") or [],
        is_open_access=bool(item.get("is_oa")),
        notes="\n".join(notes),
        project_id=project_id,
    )
    return create_journal(db, user, data), False
