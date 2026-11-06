"""Role dashboards built from SQL aggregates (no table scans in Python)."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import Select, and_, func, literal, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.conference import Conference, ProjectConference
from app.models.handbook import HandbookComment, HandbookEntry
from app.models.notification import Notification
from app.models.project import Project, ProjectMember
from app.models.research import PaperReadingProgress, ProjectPaper, ResearchPaper
from app.models.task import Task, TaskAssignment
from app.models.user import User
from app.schemas.dashboard import (
    ActivityItem,
    AdminDashboard,
    CountMap,
    DeadlineItem,
    GuestDashboard,
    HandbookItem,
    ProfessorDashboard,
    ProjectAnalytics,
    ProjectSummaryItem,
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


# --- Role dashboards -------------------------------------------------------------------


def admin_dashboard(db: Session) -> AdminDashboard:
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

    return AdminDashboard(
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
            )
        )
        .group_by(PaperReadingProgress.status)
    ).all()

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

    # Reading progress over papers linked to my projects; untouched papers
    # count as not started.
    project_papers = select(func.distinct(ProjectPaper.paper_id)).where(ProjectPaper.project_id.in_(joined))
    paper_total = db.scalar(select(func.count()).select_from(project_papers.subquery())) or 0
    statuses = dict(
        db.execute(
            select(PaperReadingProgress.status, func.count(func.distinct(PaperReadingProgress.paper_id)))
            .where(
                PaperReadingProgress.user_id == user.id,
                PaperReadingProgress.paper_id.in_(project_papers),
                PaperReadingProgress.status != "not_started",
            )
            .group_by(PaperReadingProgress.status)
        ).all()
    )
    reading_count = statuses.get("reading", 0)
    completed_count = statuses.get("completed", 0)
    reading = CountMap(
        counts={
            "not_started": max(paper_total - reading_count - completed_count, 0),
            "reading": reading_count,
            "completed": completed_count,
        },
        total=paper_total,
    )

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


