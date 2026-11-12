from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import ADMINISTRATOR, PROFESSOR, has_capability
from app.models.notification import DiscordAccount, Notification
from app.models.project import Project, ProjectMember
from app.models.research import (
    PaperReadingProgress,
    ProjectPaper,
    ResearchNote,
    ResearchPaper,
)
from app.models.user import User
from app.schemas.common import PageParams, paginate
from app.schemas.research import (
    LinkedProject,
    PaperCreate,
    PaperResponse,
    PaperUpdate,
)
from app.core.config import settings
from app.services.audit_service import record_audit
from app.services import discord_project_channels
from app.services.notification_service import enqueue_notification
from app.services.project_access import get_project_access, require, visible_project_ids


def _commit(db: Session):
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _can_view_library(user: User) -> bool:
    return has_capability(user.role_names, "research.view")


def _visible_papers_filter(user: User):
    """Full library for lab members; guests only see papers of their projects."""

    if _can_view_library(user):
        return None

    return ResearchPaper.id.in_(
        select(ProjectPaper.paper_id).where(ProjectPaper.project_id.in_(visible_project_ids(user)))
    )


def can_edit_paper(user: User, paper: ResearchPaper) -> bool:
    roles = user.role_names
    return ADMINISTRATOR in roles or PROFESSOR in roles or paper.added_by == user.id


def get_paper(db: Session, user: User, paper_id: UUID) -> ResearchPaper:
    paper = db.get(ResearchPaper, paper_id)
    if not paper:
        raise NotFoundError("Research paper not found.")

    condition = _visible_papers_filter(user)
    if condition is not None:
        visible = db.scalar(select(ResearchPaper.id).where(ResearchPaper.id == paper_id, condition))
        if not visible:
            raise NotFoundError("Research paper not found.")

    return paper


def paper_responses(db: Session, user: User, papers: list[ResearchPaper]) -> list[PaperResponse]:
    if not papers:
        return []

    ids = [paper.id for paper in papers]

    links: dict[UUID, list[LinkedProject]] = {}
    for paper_id, project_id, title in db.execute(
        select(ProjectPaper.paper_id, Project.id, Project.title)
        .join(Project, Project.id == ProjectPaper.project_id)
        .where(
            ProjectPaper.paper_id.in_(ids),
            Project.id.in_(visible_project_ids(user)),
        )
        .order_by(Project.title)
    ).all():
        links.setdefault(paper_id, []).append(LinkedProject(id=project_id, title=title))

    # The library-wide status (no project context) is shown in listings.
    statuses = dict(
        db.execute(
            select(PaperReadingProgress.paper_id, PaperReadingProgress.status).where(
                PaperReadingProgress.user_id == user.id,
                PaperReadingProgress.paper_id.in_(ids),
                PaperReadingProgress.project_id.is_(None),
            )
        ).all()
    )

    return [
        PaperResponse(
            id=paper.id,
            title=paper.title,
            authors=paper.authors,
            abstract=paper.abstract,
            publication_year=paper.publication_year,
            venue=paper.venue,
            doi=paper.doi,
            url=paper.url,
            keywords=paper.keywords,
            added_by=paper.added_by,
            created_at=paper.created_at,
            updated_at=paper.updated_at,
            projects=links.get(paper.id, []),
            my_status=statuses.get(paper.id),
            can_edit=can_edit_paper(user, paper),
            discord_thread_url=_thread_url(paper),
        )
        for paper in papers
    ]


def _thread_url(paper: ResearchPaper) -> str | None:
    if not (paper.discord_thread_id and settings.DISCORD_GUILD_ID):
        return None
    return f"https://discord.com/channels/{settings.DISCORD_GUILD_ID}/{paper.discord_thread_id}"


def list_papers(
    db: Session,
    user: User,
    params: PageParams,
    search: str | None = None,
    author: str | None = None,
    keyword: str | None = None,
    year: int | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    project_id: UUID | None = None,
    reading_status: str | None = None,
) -> tuple[list[ResearchPaper], int]:
    statement = select(ResearchPaper).order_by(ResearchPaper.created_at.desc())

    condition = _visible_papers_filter(user)
    if condition is not None:
        statement = statement.where(condition)

    if search and search.strip():
        term = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                ResearchPaper.title.ilike(term),
                ResearchPaper.abstract.ilike(term),
                ResearchPaper.venue.ilike(term),
                ResearchPaper.doi.ilike(term),
                func.array_to_string(ResearchPaper.keywords, " ").ilike(term),
                func.array_to_string(ResearchPaper.authors, " ").ilike(term),
            )
        )

    if author and author.strip():
        statement = statement.where(
            func.array_to_string(ResearchPaper.authors, "|").ilike(f"%{author.strip()}%")
        )

    if keyword and keyword.strip():
        statement = statement.where(
            func.array_to_string(ResearchPaper.keywords, "|").ilike(f"%{keyword.strip()}%")
        )

    if year is not None:
        statement = statement.where(ResearchPaper.publication_year == year)
    if year_from is not None:
        statement = statement.where(ResearchPaper.publication_year >= year_from)
    if year_to is not None:
        statement = statement.where(ResearchPaper.publication_year <= year_to)

    if project_id is not None:
        get_project_access(db, user, project_id)
        statement = statement.where(
            ResearchPaper.id.in_(
                select(ProjectPaper.paper_id).where(ProjectPaper.project_id == project_id)
            )
        )

    if reading_status:
        progress = select(PaperReadingProgress.paper_id).where(
            PaperReadingProgress.user_id == user.id,
            PaperReadingProgress.project_id.is_(None),
            PaperReadingProgress.status == reading_status,
        )
        if reading_status == "not_started":
            started = select(PaperReadingProgress.paper_id).where(
                PaperReadingProgress.user_id == user.id,
                PaperReadingProgress.project_id.is_(None),
                PaperReadingProgress.status != "not_started",
            )
            statement = statement.where(ResearchPaper.id.not_in(started))
        else:
            statement = statement.where(ResearchPaper.id.in_(progress))

    return paginate(db, statement, params)


def _find_duplicate(db: Session, doi: str | None, url: str | None) -> ResearchPaper | None:
    conditions = []
    if doi:
        conditions.append(func.lower(ResearchPaper.doi) == doi.lower())
    if url:
        conditions.append(ResearchPaper.url == url)
    if not conditions:
        return None
    return db.scalars(select(ResearchPaper).where(or_(*conditions)).limit(1)).first()


def _link(db: Session, user: User, paper_id: UUID, project_id: UUID) -> bool:
    access = get_project_access(db, user, project_id)
    require(access.can_contribute, "You cannot add papers to this project.")

    result = db.execute(
        insert(ProjectPaper)
        .values(project_id=project_id, paper_id=paper_id, added_by=user.id)
        .on_conflict_do_nothing()
        .returning(ProjectPaper.paper_id)
    )
    created = result.scalar_one_or_none() is not None
    if created:
        record_audit(
            db, user.id, "paper.linked", "research_paper", paper_id, {"project_id": project_id}
        )
        _notify_project_members(db, user, paper_id, access.project)
    return created


def _paper_summary(paper: ResearchPaper) -> str:
    authors = ", ".join(paper.authors[:4]) + (" et al." if len(paper.authors) > 4 else "")
    parts = [part for part in (authors, paper.venue, str(paper.publication_year or "")) if part]
    lines = [" · ".join(parts)] if parts else []
    if paper.doi:
        lines.append(f"https://doi.org/{paper.doi}")
    if paper.url and paper.url != f"https://doi.org/{paper.doi}":
        lines.append(paper.url)
    return "\n".join(lines)


def _notify_project_members(db: Session, user: User, paper_id: UUID, project: Project) -> None:
    """Tell the project team a paper joined their project.

    Posted in the project's private Discord channel if it has one; otherwise
    each other active member gets a DM (research category).
    """

    paper = db.get(ResearchPaper, paper_id)

    # The project's private Discord channel, when it has one, replaces the DMs.
    channel = discord_project_channels.channel_for_project(db, project.id)
    if channel is not None and project.status == "active":
        enqueue_notification(
            db,
            channel_id=channel.channel_id,
            category="research",
            event_type="paper.project_post",
            title=f"{'🎬' if _item_kind(paper) == 'video' else '📄'} New {_item_kind(paper)}: {paper.title}",
            body=f"Added to {project.title} by {user.full_name}.\n{_paper_summary(paper)}\nDiscuss it in the thread below.",
            entity_type="research_paper",
            entity_id=paper_id,
            dedupe_key=f"paper.project_post:{project.id}:{paper_id}",
        )
        return

    member_ids = db.scalars(
        select(ProjectMember.user_id).where(
            ProjectMember.project_id == project.id,
            ProjectMember.membership_status == "active",
            ProjectMember.user_id != user.id,
        )
    ).all()
    for member_id in member_ids:
        enqueue_notification(
            db,
            recipient_id=member_id,
            category="research",
            event_type="paper.linked",
            title=f"New paper in {project.title}",
            body=f"{user.full_name} added “{paper.title}”.\n{_paper_summary(paper)}",
            entity_type="research_paper",
            entity_id=paper_id,
            dedupe_key=f"paper.linked:{project.id}:{paper_id}:{member_id}",
        )


VIDEO_HOSTS = ("youtube.com", "youtu.be", "vimeo.com")


def _item_kind(paper: ResearchPaper) -> str:
    """'video' for YouTube/Vimeo links, otherwise 'paper' (wording only)."""

    host = urlparse(paper.url or "").hostname or ""
    return "video" if any(host == h or host.endswith(f".{h}") for h in VIDEO_HOSTS) else "paper"


def _lab_recipients(db: Session, exclude_user_id: UUID) -> list[UUID]:
    """Approved users with a linked Discord account who can see the whole library."""

    users = db.scalars(
        select(User)
        .join(DiscordAccount, and_(DiscordAccount.user_id == User.id, DiscordAccount.status == "linked"))
        .where(User.account_status == "approved", User.id != exclude_user_id)
    ).all()
    # Guests only see their projects' papers, so they are not told about lab-wide ones.
    return [u.id for u in users if _can_view_library(u)]


def _announce_new_paper(db: Session, user: User, paper: ResearchPaper) -> None:
    """Tell the whole lab about a general (not project) paper or video link.

    Posts to the research channel (the worker opens a discussion thread on
    the post) and DMs every lab member who has the research category on.
    Papers added to a project are only announced to that project's team
    (see ``_notify_project_members``).
    """

    kind = _item_kind(paper)
    summary = _paper_summary(paper)
    if settings.DISCORD_RESEARCH_CHANNEL_ID:
        enqueue_notification(
            db,
            channel_id=settings.DISCORD_RESEARCH_CHANNEL_ID,
            category="research",
            event_type="paper.added",
            title=f"{'🎬' if kind == 'video' else '📄'} New {kind}: {paper.title}",
            body=f"Added by {user.full_name}.\n{summary}\nDiscuss it in the thread below.",
            entity_type="research_paper",
            entity_id=paper.id,
            dedupe_key=f"paper.added:{paper.id}",
        )
    for recipient_id in _lab_recipients(db, user.id):
        enqueue_notification(
            db,
            recipient_id=recipient_id,
            category="research",
            event_type="paper.shared",
            title=f"New {kind} for the lab: {paper.title}",
            body=f"{user.full_name} added it to the research library.\n{summary}",
            entity_type="research_paper",
            entity_id=paper.id,
            dedupe_key=f"paper.shared:{paper.id}:{recipient_id}",
        )


def create_paper(db: Session, user: User, data: PaperCreate) -> tuple[ResearchPaper, bool]:
    """Create a paper, or link the existing one when the DOI/URL matches.

    Returns ``(paper, linked_existing)``.
    """

    if not has_capability(user.role_names, "research.create"):
        raise ForbiddenError("You do not have permission to add research papers.")

    url = str(data.url) if data.url else None
    duplicate = _find_duplicate(db, data.doi, url)

    if duplicate:
        if data.project_id is None:
            raise ConflictError(
                f"This paper already exists in the library (id {duplicate.id}). "
                "Link the existing record to your project instead of adding a duplicate."
            )
        _link(db, user, duplicate.id, data.project_id)
        _commit(db)
        return duplicate, True

    paper = ResearchPaper(
        title=data.title,
        authors=data.authors,
        abstract=data.abstract,
        publication_year=data.publication_year,
        venue=data.venue,
        doi=data.doi,
        url=url,
        keywords=data.keywords,
        added_by=user.id,
    )
    db.add(paper)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError("A paper with this DOI already exists.")

    record_audit(db, user.id, "paper.created", "research_paper", paper.id, {"title": paper.title})
    if data.project_id:
        # Project papers are announced to that project's team only.
        _link(db, user, paper.id, data.project_id)
    else:
        _announce_new_paper(db, user, paper)

    _commit(db)
    db.refresh(paper)
    return paper, False


def update_paper(db: Session, user: User, paper_id: UUID, data: PaperUpdate) -> ResearchPaper:
    paper = get_paper(db, user, paper_id)
    require(can_edit_paper(user, paper), "You cannot edit this paper's metadata.")

    changes = data.model_dump(exclude_unset=True)
    if "title" in changes and not (changes["title"] or "").strip():
        raise ConflictError("Title cannot be empty.")

    if changes.get("doi") and changes["doi"] != paper.doi:
        duplicate = _find_duplicate(db, changes["doi"], None)
        if duplicate and duplicate.id != paper.id:
            raise ConflictError("Another paper already uses this DOI.")

    for field, value in changes.items():
        if field == "url":
            value = str(value) if value else None
        if field in ("authors", "keywords") and value is None:
            value = []
        if field == "abstract" and value is None:
            value = ""
        setattr(paper, field, value)

    if changes:
        record_audit(db, user.id, "paper.updated", "research_paper", paper.id, {"fields": sorted(changes)})

    _commit(db)
    db.refresh(paper)
    return paper


def delete_paper(db: Session, user: User, paper_id: UUID) -> None:
    """Hard-delete a paper with its project links, reading progress and notes.

    Administrators may delete any paper. The person who added it, and
    professors, may delete it only while no project uses it and nobody
    else has private notes on it, so other people's work is never lost.
    """

    paper = get_paper(db, user, paper_id)
    require(can_edit_paper(user, paper), "You cannot delete this paper.")

    if ADMINISTRATOR not in user.role_names:
        linked = db.scalar(select(func.count()).select_from(ProjectPaper).where(ProjectPaper.paper_id == paper_id))
        require(not linked, "This paper is used by a project. Remove it from its projects first, or ask an administrator.")
        others_notes = db.scalar(
            select(func.count()).select_from(ResearchNote).where(
                ResearchNote.paper_id == paper_id, ResearchNote.user_id != user.id
            )
        )
        require(not others_notes, "Other lab members have notes on this paper. Ask an administrator to delete it.")

    # Do not announce a paper that no longer exists.
    db.execute(
        update(Notification)
        .where(
            Notification.entity_type == "research_paper",
            Notification.entity_id == str(paper_id),
            Notification.status.in_(("pending", "retry_scheduled")),
        )
        .values(status="failed", last_error="Paper was deleted before delivery.")
    )
    record_audit(
        db, user.id, "paper.deleted", "research_paper", paper_id, {"title": paper.title, "doi": paper.doi}
    )
    # Links, reading progress and notes are removed by ON DELETE CASCADE.
    db.delete(paper)
    _commit(db)


def link_paper(db: Session, user: User, paper_id: UUID, project_id: UUID) -> ResearchPaper:
    paper = get_paper(db, user, paper_id)
    if not _link(db, user, paper.id, project_id):
        raise ConflictError("The paper is already linked to this project.")
    _commit(db)
    return paper


def unlink_paper(db: Session, user: User, paper_id: UUID, project_id: UUID) -> None:
    access = get_project_access(db, user, project_id)
    link = db.get(ProjectPaper, (project_id, paper_id))
    if not link:
        raise NotFoundError("The paper is not linked to this project.")

    require(
        access.is_active and (access.is_manager or (access.can_contribute and link.added_by == user.id)),
        "You cannot remove this paper from the project.",
    )

    db.delete(link)
    record_audit(db, user.id, "paper.unlinked", "research_paper", paper_id, {"project_id": project_id})
    _commit(db)


# --- Reading progress --------------------------------------------------------------


def set_reading_status(
    db: Session, user: User, paper_id: UUID, status: str, project_id: UUID | None
) -> PaperReadingProgress:
    if not has_capability(user.role_names, "research.track_progress"):
        raise ForbiddenError("Your role cannot track reading progress.")

    get_paper(db, user, paper_id)

    if project_id is not None:
        access = get_project_access(db, user, project_id)
        require(access.role in ("owner", "member", "supervisor"), "You are not a member of this project.")
        if not db.get(ProjectPaper, (project_id, paper_id)):
            raise NotFoundError("The paper is not linked to this project.")

    statement = (
        insert(PaperReadingProgress)
        .values(user_id=user.id, paper_id=paper_id, project_id=project_id, status=status)
        .on_conflict_do_update(
            constraint="uq_paper_reading_progress_user_paper_project",
            set_={"status": status, "updated_at": func.now()},
        )
        .returning(PaperReadingProgress.id)
    )
    progress_id = db.execute(statement).scalar_one()
    _commit(db)
    return db.get(PaperReadingProgress, progress_id)


def my_reading_progress(db: Session, user: User):
    return db.execute(
        select(PaperReadingProgress, ResearchPaper.title)
        .join(ResearchPaper, ResearchPaper.id == PaperReadingProgress.paper_id)
        .where(PaperReadingProgress.user_id == user.id)
        .order_by(PaperReadingProgress.updated_at.desc())
    ).all()


def project_reading_progress(db: Session, user: User, project_id: UUID):
    """Reading status of project members (status only, never notes)."""

    access = get_project_access(db, user, project_id)
    require(access.is_manager, "Only project supervisors can view member reading progress.")

    return db.execute(
        select(PaperReadingProgress, ResearchPaper.title, User.username)
        .join(ResearchPaper, ResearchPaper.id == PaperReadingProgress.paper_id)
        .join(User, User.id == PaperReadingProgress.user_id)
        .join(
            ProjectPaper,
            and_(
                ProjectPaper.paper_id == PaperReadingProgress.paper_id,
                ProjectPaper.project_id == project_id,
            ),
        )
        .where(
            or_(
                PaperReadingProgress.project_id == project_id,
                PaperReadingProgress.project_id.is_(None),
            )
        )
        .where(
            PaperReadingProgress.user_id.in_(
                select(ProjectMember.user_id).where(
                    ProjectMember.project_id == project_id,
                    ProjectMember.membership_status == "active",
                )
            )
        )
        .order_by(User.username, ResearchPaper.title)
    ).all()


# --- Private notes -----------------------------------------------------------------
# Notes are filtered by user_id in every query; there is deliberately no
# code path that returns another user's notes, administrators included.


def list_notes(db: Session, user: User, paper_id: UUID) -> list[ResearchNote]:
    get_paper(db, user, paper_id)
    return list(
        db.scalars(
            select(ResearchNote)
            .where(ResearchNote.paper_id == paper_id, ResearchNote.user_id == user.id)
            .order_by(ResearchNote.created_at.desc())
        ).all()
    )


def create_note(db: Session, user: User, paper_id: UUID, content: str, project_id: UUID | None) -> ResearchNote:
    if not _can_view_library(user):
        raise ForbiddenError("You cannot add research notes.")
    get_paper(db, user, paper_id)
    if project_id is not None:
        get_project_access(db, user, project_id)

    note = ResearchNote(user_id=user.id, paper_id=paper_id, project_id=project_id, content=content)
    db.add(note)
    _commit(db)
    db.refresh(note)
    return note


def _own_note(db: Session, user: User, note_id: UUID) -> ResearchNote:
    note = db.scalar(select(ResearchNote).where(ResearchNote.id == note_id, ResearchNote.user_id == user.id))
    if not note:
        raise NotFoundError("Note not found.")
    return note


def update_note(db: Session, user: User, note_id: UUID, content: str) -> ResearchNote:
    note = _own_note(db, user, note_id)
    note.content = content
    _commit(db)
    db.refresh(note)
    return note


def delete_note(db: Session, user: User, note_id: UUID) -> None:
    note = _own_note(db, user, note_id)
    db.delete(note)
    _commit(db)
