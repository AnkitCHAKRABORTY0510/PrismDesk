"""Role dashboards built from SQL aggregates (no table scans in Python)."""

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import Select, and_, case, func, literal, select, union
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.conference import Conference, ProjectConference
from app.models.handbook import HandbookComment, HandbookEntry
from app.models.notification import Notification
from app.models.project import Project, ProjectMember
from app.models.project_link import ProjectRepoLink
from app.models.research import PaperReadingProgress, ProjectPaper, ResearchPaper
from app.models.task import Task, TaskAssignment
from app.models.user import User
from app.schemas.dashboard import (
    ActivityItem,
    AdminDashboard,
    CountMap,
    DayCount,
    DeadlineItem,
    GuestDashboard,
    HandbookItem,
    MemberChip,
    MemberReading,
    ProfessorDashboard,
    ProjectAnalytics,
    ProjectSummaryItem,
    ReadingListItem,
    RepoLinkChip,
    ReviewItem,
    StudentDashboard,
    WeeklyCount,
)
from app.services.project_access import get_project_access, require

ASSIGNMENT_STATUSES = ("todo", "in_progress", "under_review", "revision_required", "completed")
READING_STATUSES = ("not_started", "reading", "completed")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _count_map(rows, keys) -> CountMap:
    counts = {key: 0 for key in keys}
    for key, value in rows:
        counts[key] = value
    return CountMap(counts=counts, total=sum(counts.values()))


def _member_projects(user_id: UUID, roles: tuple[str, ...]) -> Select:
    return (
        select(ProjectMember.project_id)
        .join(Project, Project.id == ProjectMember.project_id)
        .where(
            ProjectMember.user_id == user_id,
            ProjectMember.membership_status == "active",
            ProjectMember.membership_role.in_(roles),
            Project.status != "deleted",
        )
    )


def _project_summaries(db: Session, user: User, project_ids: Select) -> list[ProjectSummaryItem]:
    now = _now()
    member_counts = (
        select(ProjectMember.project_id, func.count().label("members"))
        .where(ProjectMember.membership_status == "active")
        .group_by(ProjectMember.project_id)
        .subquery()
    )
    task_stats = (
        select(
            Task.project_id,
            func.count(TaskAssignment.id).label("total"),
            func.count(TaskAssignment.id).filter(TaskAssignment.status == "completed").label("completed"),
            func.count(TaskAssignment.id).filter(TaskAssignment.status == "under_review").label("reviews"),
            func.count(TaskAssignment.id)
            .filter(and_(TaskAssignment.status != "completed", Task.due_at < now))
            .label("overdue"),
        )
        .join(TaskAssignment, TaskAssignment.task_id == Task.id)
        .where(Task.task_type == "official")
        .group_by(Task.project_id)
        .subquery()
    )
    my_role = (
        select(ProjectMember.project_id, ProjectMember.membership_role)
        .where(ProjectMember.user_id == user.id, ProjectMember.membership_status == "active")
        .subquery()
    )

    rows = db.execute(
        select(
            Project.id,
            Project.title,
            Project.status,
            my_role.c.membership_role,
            func.coalesce(member_counts.c.members, 0),
            func.coalesce(task_stats.c.total, 0),
            func.coalesce(task_stats.c.completed, 0),
            func.coalesce(task_stats.c.reviews, 0),
            func.coalesce(task_stats.c.overdue, 0),
        )
        .outerjoin(member_counts, member_counts.c.project_id == Project.id)
        .outerjoin(task_stats, task_stats.c.project_id == Project.id)
        .outerjoin(my_role, my_role.c.project_id == Project.id)
        .where(Project.id.in_(project_ids))
        .order_by(Project.status, Project.updated_at.desc())
        .limit(50)
    ).all()

    ids = [row[0] for row in rows]
    pipelines: dict[UUID, dict[str, int]] = {}
    members: dict[UUID, list[MemberChip]] = {}
    links: dict[UUID, list[RepoLinkChip]] = {}
    if ids:
        for project_id, status, count in db.execute(
            select(Task.project_id, TaskAssignment.status, func.count())
            .join(TaskAssignment, TaskAssignment.task_id == Task.id)
            .where(Task.project_id.in_(ids), Task.task_type == "official")
            .group_by(Task.project_id, TaskAssignment.status)
        ).all():
            pipelines.setdefault(project_id, {key: 0 for key in ASSIGNMENT_STATUSES})[status] = count

        role_order = case(
            (ProjectMember.membership_role == "owner", 0),
            (ProjectMember.membership_role == "supervisor", 1),
            (ProjectMember.membership_role == "member", 2),
            else_=3,
        )
        ranked = (
            select(
                ProjectMember.project_id,
                ProjectMember.user_id,
                ProjectMember.membership_role,
                func.row_number()
                .over(partition_by=ProjectMember.project_id, order_by=(role_order, ProjectMember.joined_at))
                .label("rank"),
            )
            .where(ProjectMember.project_id.in_(ids), ProjectMember.membership_status == "active")
            .subquery()
        )
        for project_id, user_id, username, full_name, role in db.execute(
            select(ranked.c.project_id, User.id, User.username, User.full_name, ranked.c.membership_role)
            .join(User, User.id == ranked.c.user_id)
            .where(ranked.c.rank <= 5)
            .order_by(ranked.c.project_id, ranked.c.rank)
        ).all():
            members.setdefault(project_id, []).append(
                MemberChip(user_id=user_id, username=username, full_name=full_name, membership_role=role)
            )

        for project_id, url, label in db.execute(
            select(ProjectRepoLink.project_id, ProjectRepoLink.url, ProjectRepoLink.label)
            .where(ProjectRepoLink.project_id.in_(ids))
            .order_by(ProjectRepoLink.created_at)
        ).all():
            bucket = links.setdefault(project_id, [])
            if len(bucket) < 3:
                bucket.append(RepoLinkChip(url=url, label=label))

    return [
        ProjectSummaryItem(
            id=row[0],
            title=row[1],
            status=row[2],
            my_role=row[3],
            member_count=row[4],
            assignments_total=row[5],
            assignments_completed=row[6],
            pending_reviews=row[7],
            overdue=row[8],
            assignment_counts=pipelines.get(row[0], {key: 0 for key in ASSIGNMENT_STATUSES}),
            members=members.get(row[0], []),
            repo_links=links.get(row[0], []),
        )
        for row in rows
    ]


def _upcoming_conferences(db: Session, project_ids: Select | None, limit: int = 5) -> list[DeadlineItem]:
    statement = (
        select(Conference.id, Conference.name, Conference.submission_deadline)
        .where(Conference.submission_deadline >= func.now())
        .order_by(Conference.submission_deadline)
        .limit(limit)
    )
    if project_ids is not None:
        statement = statement.where(
            Conference.id.in_(
                select(ProjectConference.conference_id).where(
                    ProjectConference.project_id.in_(project_ids),
                    ProjectConference.status == "active",
                )
            )
        )
    return [
        DeadlineItem(id=cid, title=name, due_at=deadline, kind="conference")
        for cid, name, deadline in db.execute(statement).all()
    ]


def _upcoming_tasks(db: Session, condition, limit: int = 5) -> list[DeadlineItem]:
    open_assignment = (
        select(TaskAssignment.id)
        .where(TaskAssignment.task_id == Task.id, TaskAssignment.status != "completed", condition)
        .exists()
    )
    rows = db.execute(
        select(Task.id, Task.title, Task.due_at, Task.project_id, Project.title)
        .outerjoin(Project, Project.id == Task.project_id)
        .where(
            open_assignment,
            Task.task_type != "reminder",
            Task.due_at.is_not(None),
            Task.due_at >= func.now(),
            (Task.project_id.is_(None)) | (Project.status == "active"),
        )
        .order_by(Task.due_at)
        .limit(limit)
    ).all()
    return [
        DeadlineItem(id=r[0], title=r[1], due_at=r[2], kind="task", project_id=r[3], project_title=r[4])
        for r in rows
    ]


def _handbook_items(db: Session, condition, limit: int = 10) -> list[HandbookItem]:
    comment_counts = (
        select(HandbookComment.entry_id, func.count().label("comments"))
        .group_by(HandbookComment.entry_id)
        .subquery()
    )
    rows = db.execute(
        select(
            HandbookEntry.id,
            HandbookEntry.entry_date,
            User.username,
            Project.id,
            Project.title,
            func.coalesce(comment_counts.c.comments, 0),
        )
        .join(User, User.id == HandbookEntry.student_id)
        .join(Project, Project.id == HandbookEntry.project_id)
        .outerjoin(comment_counts, comment_counts.c.entry_id == HandbookEntry.id)
        .where(condition, Project.status != "deleted")
        .order_by(HandbookEntry.entry_date.desc(), HandbookEntry.updated_at.desc())
        .limit(limit)
    ).all()
    return [
        HandbookItem(id=r[0], entry_date=r[1], student_username=r[2], project_id=r[3], project_title=r[4], comment_count=r[5])
        for r in rows
    ]


def _effective_status(user_id: UUID | None = None):
    """One reading status per (user, paper): the library-wide row wins,
    otherwise the most recently updated project-scoped row."""

    statement = (
        select(PaperReadingProgress.user_id, PaperReadingProgress.paper_id, PaperReadingProgress.status)
        .distinct(PaperReadingProgress.user_id, PaperReadingProgress.paper_id)
        .order_by(
            PaperReadingProgress.user_id,
            PaperReadingProgress.paper_id,
            PaperReadingProgress.project_id.is_(None).desc(),
            PaperReadingProgress.updated_at.desc(),
        )
    )
    if user_id is not None:
        statement = statement.where(PaperReadingProgress.user_id == user_id)
    return statement.subquery()


def _my_reading(db: Session, user: User, project_ids: Select, limit: int = 8) -> tuple[CountMap, list[ReadingListItem]]:
    """The user's own reading status over papers linked to their projects
    plus any paper they have set a status on. Untouched papers are "to read"."""

    candidates = union(
        select(ProjectPaper.paper_id).where(ProjectPaper.project_id.in_(project_ids)),
        select(PaperReadingProgress.paper_id).where(PaperReadingProgress.user_id == user.id),
    ).subquery()
    effective = _effective_status(user.id)
    status = func.coalesce(effective.c.status, "not_started")

    counts = _count_map(
        db.execute(
            select(status, func.count())
            .select_from(ResearchPaper)
            .outerjoin(effective, effective.c.paper_id == ResearchPaper.id)
            .where(ResearchPaper.id.in_(select(candidates.c.paper_id)))
            .group_by(status)
        ).all(),
        READING_STATUSES,
    )

    order = case((status == "reading", 0), (status == "not_started", 1), else_=2)
    rows = db.execute(
        select(ResearchPaper.id, ResearchPaper.title, ResearchPaper.venue, ResearchPaper.publication_year, status)
        .outerjoin(effective, effective.c.paper_id == ResearchPaper.id)
        .where(ResearchPaper.id.in_(select(candidates.c.paper_id)))
        .order_by(order, ResearchPaper.created_at.desc())
        .limit(limit)
    ).all()
    return counts, [
        ReadingListItem(paper_id=r[0], title=r[1], venue=r[2], publication_year=r[3], status=r[4]) for r in rows
    ]


def _member_reading(db: Session, user: User, supervised: Select, limit: int = 20) -> list[MemberReading]:
    """Per-member reading status over the papers of the projects they belong to."""

    member_papers = (
        select(ProjectMember.user_id, ProjectPaper.paper_id)
        .join(ProjectPaper, ProjectPaper.project_id == ProjectMember.project_id)
        .where(
            ProjectMember.project_id.in_(supervised),
            ProjectMember.membership_status == "active",
            ProjectMember.membership_role.in_(("owner", "member")),
            ProjectMember.user_id != user.id,
        )
        .distinct()
        .subquery()
    )
    effective = _effective_status()
    status = func.coalesce(effective.c.status, "not_started")
    rows = db.execute(
        select(User.id, User.username, User.full_name, status, func.count())
        .select_from(member_papers)
        .join(User, User.id == member_papers.c.user_id)
        .outerjoin(
            effective,
            and_(effective.c.user_id == member_papers.c.user_id, effective.c.paper_id == member_papers.c.paper_id),
        )
        .group_by(User.id, User.username, User.full_name, status)
        .order_by(User.username)
    ).all()

    grid: dict[UUID, MemberReading] = {}
    for user_id, username, full_name, state, count in rows:
        item = grid.setdefault(
            user_id,
            MemberReading(
                user_id=user_id,
                username=username,
                full_name=full_name,
                counts={key: 0 for key in READING_STATUSES},
                total=0,
            ),
        )
        item.counts[state] = count
        item.total += count
    return list(grid.values())[:limit]


def _handbook_days(db: Session, user: User, days: int = 84) -> tuple[list[DayCount], int]:
    # Handbook entry dates are the lab's local calendar days (the handbook
    # module also uses the server's local date).
    today = date.today()
    rows = db.execute(
        select(HandbookEntry.entry_date, func.count())
        .where(HandbookEntry.student_id == user.id, HandbookEntry.entry_date > today - timedelta(days=days))
        .group_by(HandbookEntry.entry_date)
        .order_by(HandbookEntry.entry_date)
    ).all()
    active = {day for day, _ in rows}

    # Streak of consecutive days with an entry, ending today (or yesterday
    # when today has no entry yet, so the streak doesn't reset at midnight).
    streak = 0
    cursor = today if today in active else today - timedelta(days=1)
    while cursor in active:
        streak += 1
        cursor -= timedelta(days=1)
    return [DayCount(day=day, count=count) for day, count in rows], streak


def _open_reminders(db: Session, user: User) -> int:
    """Reminders sent to the user that they have not ticked off yet."""

    return db.scalar(
        select(func.count())
        .select_from(TaskAssignment)
        .join(Task, Task.id == TaskAssignment.task_id)
        .join(Project, Project.id == Task.project_id)
        .where(
            Task.task_type == "reminder",
            TaskAssignment.assignee_id == user.id,
            TaskAssignment.status != "completed",
            Project.status == "active",
        )
    ) or 0


# --- Role dashboards -------------------------------------------------------------------


def admin_dashboard(db: Session, user: User | None = None) -> AdminDashboard:
    users = db.execute(select(User.account_status, func.count()).group_by(User.account_status)).all()
    projects = db.execute(select(Project.status, func.count()).group_by(Project.status)).all()
    tasks = db.execute(
        select(TaskAssignment.status, func.count())
        .join(Task, Task.id == TaskAssignment.task_id)
        .where(Task.task_type == "official")
        .group_by(TaskAssignment.status)
    ).all()
    overdue = db.scalar(
        select(func.count())
        .select_from(TaskAssignment)
        .join(Task, Task.id == TaskAssignment.task_id)
        .where(Task.task_type == "official", Task.due_at < func.now(), TaskAssignment.status != "completed")
    )
    notifications = db.execute(select(Notification.status, func.count()).group_by(Notification.status)).all()

    activity = db.execute(
        select(AuditLog, User.username)
        .outerjoin(User, User.id == AuditLog.actor_user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(10)
    ).all()

    if user is not None:
        my_reading, reading_list = _my_reading(db, user, _member_projects(user.id, ("owner", "supervisor", "member")))
    else:
        my_reading, reading_list = _count_map([], READING_STATUSES), []

    return AdminDashboard(
        my_reading=my_reading,
        reading_list=reading_list,
        users=_count_map(users, ("pending", "approved", "rejected", "suspended")),
        projects=_count_map(projects, ("active", "archived", "deleted")),
        research_papers=db.scalar(select(func.count()).select_from(ResearchPaper)) or 0,
        tasks=_count_map(tasks, ASSIGNMENT_STATUSES),
        overdue_assignments=overdue or 0,
        notifications=_count_map(notifications, ("pending", "processing", "sent", "failed", "retry_scheduled")),
        upcoming_conferences=_upcoming_conferences(db, None),
        recent_activity=[
            ActivityItem(
                id=log.id,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                actor_username=username,
                created_at=log.created_at,
            )
            for log, username in activity
        ],
    )


def professor_dashboard(db: Session, user: User) -> ProfessorDashboard:
    supervised = _member_projects(user.id, ("owner", "supervisor"))

    members = db.scalar(
        select(func.count(func.distinct(ProjectMember.user_id))).where(
            ProjectMember.project_id.in_(supervised),
            ProjectMember.membership_status == "active",
            ProjectMember.user_id != user.id,
        )
    )

    review_rows = db.execute(
        select(TaskAssignment.id, Task.id, Task.title, User.username, Project.title, TaskAssignment.submitted_at)
        .join(Task, Task.id == TaskAssignment.task_id)
        .join(Project, Project.id == Task.project_id)
        .join(User, User.id == TaskAssignment.assignee_id)
        .where(
            Task.project_id.in_(supervised),
            Task.task_type == "official",
            TaskAssignment.status == "under_review",
            TaskAssignment.assignee_id != user.id,
        )
        .order_by(TaskAssignment.submitted_at)
    ).all()

    reading = db.execute(
        select(PaperReadingProgress.status, func.count())
        .join(
            ProjectPaper,
            and_(
                ProjectPaper.paper_id == PaperReadingProgress.paper_id,
                ProjectPaper.project_id.in_(supervised),
            ),
        )
        .where(
            PaperReadingProgress.user_id.in_(
                select(ProjectMember.user_id).where(
                    ProjectMember.project_id.in_(supervised), ProjectMember.membership_status == "active"
                )
            ),
            PaperReadingProgress.user_id != user.id,
        )
        .group_by(PaperReadingProgress.status)
    ).all()
    my_reading, reading_list = _my_reading(db, user, supervised)

    deadlines = _upcoming_tasks(db, Task.project_id.in_(supervised)) + _upcoming_conferences(db, supervised)
    deadlines.sort(key=lambda item: item.due_at)

    return ProfessorDashboard(
        supervised_projects=_project_summaries(db, user, supervised),
        member_count=members or 0,
        pending_reviews=len(review_rows),
        review_queue=[
            ReviewItem(
                assignment_id=r[0], task_id=r[1], task_title=r[2], student_username=r[3], project_title=r[4], submitted_at=r[5]
            )
            for r in review_rows[:10]
        ],
        recent_handbook_entries=_handbook_items(db, HandbookEntry.project_id.in_(supervised)),
        upcoming_deadlines=deadlines[:10],
        reading_progress=_count_map(reading, READING_STATUSES),
        my_reading=my_reading,
        reading_list=reading_list,
        member_reading=_member_reading(db, user, supervised),
        open_reminders=_open_reminders(db, user),
    )


def student_dashboard(db: Session, user: User) -> StudentDashboard:
    joined = _member_projects(user.id, ("owner", "member"))
    owned = db.scalar(
        select(func.count()).select_from(Project).where(Project.owner_id == user.id, Project.status != "deleted")
    )

    def assignment_counts(task_type: str):
        return db.execute(
            select(TaskAssignment.status, func.count())
            .join(Task, Task.id == TaskAssignment.task_id)
            .outerjoin(Project, Project.id == Task.project_id)
            .where(
                TaskAssignment.assignee_id == user.id,
                Task.task_type == task_type,
                (Task.project_id.is_(None)) | (Project.status != "deleted"),
            )
            .group_by(TaskAssignment.status)
        ).all()

    assigned = _count_map(assignment_counts("official"), ASSIGNMENT_STATUSES)
    personal = _count_map(assignment_counts("personal"), ("todo", "in_progress", "completed"))
    pending = sum(assigned.counts[s] for s in ("todo", "in_progress", "revision_required"))
    completion = assigned.counts["completed"] / assigned.total if assigned.total else 0.0

    # My reading status over papers linked to my projects (and any paper I
    # track); untouched papers count as "to read".
    reading, reading_list = _my_reading(db, user, joined)
    handbook_days, streak = _handbook_days(db, user)

    today = _now().date()
    entries_since = lambda days: db.scalar(  # noqa: E731
        select(func.count())
        .select_from(HandbookEntry)
        .where(HandbookEntry.student_id == user.id, HandbookEntry.entry_date > today - timedelta(days=days))
    ) or 0

    deadlines = _upcoming_tasks(db, TaskAssignment.assignee_id == user.id) + _upcoming_conferences(db, joined)
    deadlines.sort(key=lambda item: item.due_at)

    return StudentDashboard(
        joined_projects=_project_summaries(db, user, joined),
        owned_project_count=owned or 0,
        assigned_tasks=assigned,
        personal_tasks=personal,
        pending_submissions=pending,
        task_completion_rate=round(completion, 3),
        reading_progress=reading,
        handbook_entries_last_7_days=entries_since(7),
        handbook_entries_last_30_days=entries_since(30),
        recent_handbook_entries=_handbook_items(db, HandbookEntry.student_id == user.id, limit=5),
        upcoming_deadlines=deadlines[:10],
        reading_list=reading_list,
        handbook_days=handbook_days,
        handbook_streak=streak,
        open_reminders=_open_reminders(db, user),
    )


def guest_dashboard(db: Session, user: User) -> GuestDashboard:
    granted = _member_projects(user.id, ("guest",))
    papers = db.scalar(
        select(func.count(func.distinct(ProjectPaper.paper_id))).where(ProjectPaper.project_id.in_(granted))
    )
    return GuestDashboard(
        projects=_project_summaries(db, user, granted),
        paper_count=papers or 0,
        upcoming_conferences=_upcoming_conferences(db, granted),
    )


def project_analytics(db: Session, user: User, project_id: UUID) -> ProjectAnalytics:
    access = get_project_access(db, user, project_id)
    require(access.is_manager, "Only project supervisors can view project analytics.")

    assignments = _count_map(
        db.execute(
            select(TaskAssignment.status, func.count())
            .join(Task, Task.id == TaskAssignment.task_id)
            .where(Task.project_id == project_id, Task.task_type == "official")
            .group_by(TaskAssignment.status)
        ).all(),
        ASSIGNMENT_STATUSES,
    )
    overdue = db.scalar(
        select(func.count())
        .select_from(TaskAssignment)
        .join(Task, Task.id == TaskAssignment.task_id)
        .where(
            Task.project_id == project_id,
            Task.task_type == "official",
            Task.due_at < func.now(),
            TaskAssignment.status != "completed",
        )
    )
    paper_count = db.scalar(select(func.count()).select_from(ProjectPaper).where(ProjectPaper.project_id == project_id))
    reading = _count_map(
        db.execute(
            select(PaperReadingProgress.status, func.count())
            .join(
                ProjectPaper,
                and_(ProjectPaper.paper_id == PaperReadingProgress.paper_id, ProjectPaper.project_id == project_id),
            )
            .where(
                PaperReadingProgress.user_id.in_(
                    select(ProjectMember.user_id).where(
                        ProjectMember.project_id == project_id, ProjectMember.membership_status == "active"
                    )
                )
            )
            .group_by(PaperReadingProgress.status)
        ).all(),
        READING_STATUSES,
    )

    since = _now().date() - timedelta(weeks=8)
    week = func.date_trunc("week", HandbookEntry.entry_date).label("week")
    weekly = db.execute(
        select(week, func.count())
        .where(HandbookEntry.project_id == project_id, HandbookEntry.entry_date >= since)
        .group_by(week)
        .order_by(week)
    ).all()

    activity = db.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(
            AuditLog.entity_type == "project",
            AuditLog.entity_id == str(project_id),
            AuditLog.created_at >= _now() - timedelta(days=30),
        )
    )

    deadlines = _upcoming_tasks(db, Task.project_id == project_id) + _upcoming_conferences(
        db, select(literal(project_id))
    )
    deadlines.sort(key=lambda item: item.due_at)

    return ProjectAnalytics(
        project_id=project_id,
        assignments=assignments,
        completion_rate=round(assignments.counts["completed"] / assignments.total, 3) if assignments.total else 0.0,
        overdue_assignments=overdue or 0,
        reading_progress=reading,
        paper_count=paper_count or 0,
        handbook_per_week=[WeeklyCount(week_start=w.date(), count=c) for w, c in weekly],
        activity_last_30_days=activity or 0,
        upcoming_deadlines=deadlines[:10],
    )


