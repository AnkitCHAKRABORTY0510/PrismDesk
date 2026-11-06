from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import STUDENT, has_capability
from app.models.project import Project, ProjectMember
from app.models.task import Task, TaskAssignment, TaskReview, TaskSubmission
from app.models.user import User
from app.schemas.admin import user_summary
from app.schemas.common import PageParams, paginate
from app.schemas.task import (
    AssignmentResponse,
    ReviewResponse,
    SubmissionCreate,
    SubmissionResponse,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
from app.services.audit_service import record_audit
from app.services.notification_service import enqueue_notification
from app.services.project_access import (
    ProjectAccess,
    get_project_access,
    managed_project_ids,
    require,
)

# Status changes an assignee may make directly. "under_review" is only
# reached by submitting, "completed"/"revision_required" (for official
# tasks) only by a reviewer.
OFFICIAL_ASSIGNEE_TRANSITIONS = {
    "todo": {"in_progress"},
    "in_progress": {"todo"},
    "revision_required": {"in_progress"},
    "under_review": set(),
    "completed": set(),
}

PERSONAL_TRANSITIONS = {
    "todo": {"in_progress", "completed"},
    "in_progress": {"todo", "completed"},
    "completed": {"in_progress"},
    "under_review": set(),
    "revision_required": set(),
}

SUBMITTABLE_STATUSES = {"todo", "in_progress", "revision_required"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _commit(db: Session):
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _assignment_response(assignment: TaskAssignment, submission_count: int = 0) -> AssignmentResponse:
    return AssignmentResponse(
        id=assignment.id,
        task_id=assignment.task_id,
        assignee=user_summary(assignment.assignee),
        status=assignment.status,
        assigned_at=assignment.assigned_at,
        submitted_at=assignment.submitted_at,
        completed_at=assignment.completed_at,
        updated_at=assignment.updated_at,
        submission_count=submission_count,
    )


def _is_overdue(task: Task, assignments: list[TaskAssignment]) -> bool:
    if not task.due_at or task.due_at >= _now():
        return False
    return any(a.status != "completed" for a in assignments)


# --- Access helpers -----------------------------------------------------------------


class TaskContext:
    def __init__(self, task: Task, user: User, project_access: ProjectAccess | None):
        self.task = task
        self.user = user
        self.project_access = project_access

    @property
    def is_personal_owner(self) -> bool:
        return self.task.task_type == "personal" and self.task.created_by == self.user.id

    @property
    def can_manage(self) -> bool:
        if self.task.task_type == "personal":
            return self.is_personal_owner
        return bool(self.project_access and self.project_access.is_manager)

    @property
    def can_modify(self) -> bool:
        if self.task.task_type == "personal":
            return self.is_personal_owner
        return bool(self.project_access and self.project_access.is_manager and self.project_access.is_active)


def _load_context(db: Session, user: User, task_id: UUID) -> TaskContext:
    task = db.get(Task, task_id)
    if not task:
        raise NotFoundError("Task not found.")

    if task.task_type == "personal":
        # Personal tasks are private to their creator.
        if task.created_by != user.id:
            raise NotFoundError("Task not found.")
        return TaskContext(task, user, None)

    try:
        access = get_project_access(db, user, task.project_id)
    except NotFoundError:
        raise NotFoundError("Task not found.")

    context = TaskContext(task, user, access)
    if not context.can_manage:
        assigned = db.scalar(
            select(TaskAssignment.id).where(
                TaskAssignment.task_id == task.id, TaskAssignment.assignee_id == user.id
            )
        )
        if not assigned:
            raise NotFoundError("Task not found.")

    return context


def _load_assignment(db: Session, user: User, assignment_id: UUID) -> tuple[TaskAssignment, TaskContext]:
    assignment = db.get(TaskAssignment, assignment_id)
    if not assignment:
        raise NotFoundError("Assignment not found.")

    context = _load_context(db, user, assignment.task_id)
    if assignment.assignee_id != user.id and not context.can_manage:
        # Students never see other students' assignments or submissions.
        raise NotFoundError("Assignment not found.")

    return assignment, context


def _validate_assignees(db: Session, project_id: UUID, assignee_ids: list[UUID]) -> list[User]:
    unique_ids = list(dict.fromkeys(assignee_ids))
    rows = db.execute(
        select(User, ProjectMember.membership_role)
        .join(ProjectMember, ProjectMember.user_id == User.id)
        .where(
            ProjectMember.project_id == project_id,
            ProjectMember.membership_status == "active",
            User.id.in_(unique_ids),
        )
    ).all()

    found = {user.id: (user, role) for user, role in rows}
    users = []
    for assignee_id in unique_ids:
        if assignee_id not in found:
            raise BadRequestError("Assignees must be active members of the project.")
        user, role = found[assignee_id]
        if STUDENT not in user.role_names or role not in ("owner", "member"):
            raise BadRequestError("Official tasks can only be assigned to student members.")
        if user.account_status != "approved":
            raise BadRequestError("Assignees must have approved accounts.")
        users.append(user)
    return users


def _assign(db: Session, actor: User, task: Task, assignees: list[User]) -> list[TaskAssignment]:
    existing = set(
        db.scalars(select(TaskAssignment.assignee_id).where(TaskAssignment.task_id == task.id)).all()
    )
    created = []
    for assignee in assignees:
        if assignee.id in existing:
            continue
        assignment = TaskAssignment(task_id=task.id, assignee_id=assignee.id, assigned_by=actor.id)
        db.add(assignment)
        created.append(assignment)
        enqueue_notification(
            db,
            recipient_id=assignee.id,
            category="tasks",
            event_type="task.assigned",
            title="New task assigned",
            body=f"You were assigned “{task.title}”."
            + (f" Due {task.due_at:%Y-%m-%d %H:%M UTC}." if task.due_at else ""),
            entity_type="task",
            entity_id=task.id,
            dedupe_key=f"task.assigned:{task.id}:{assignee.id}",
        )
    if created:
        record_audit(
            db, actor.id, "task.assigned", "task", task.id,
            {"assignee_ids": [a.id for a in assignees if a.id not in existing]},
        )
    return created


# --- Tasks ----------------------------------------------------------------------------


def create_task(db: Session, user: User, data: TaskCreate) -> Task:
    if data.task_type == "personal":
        if not has_capability(user.role_names, "tasks.personal"):
            raise ForbiddenError("Only students can create personal tasks.")
        if data.project_id is not None:
            access = get_project_access(db, user, data.project_id)
            require(access.can_contribute, "You cannot add tasks to this project.")
    else:
        if not has_capability(user.role_names, "tasks.create_official"):
            raise ForbiddenError("You cannot create official tasks.")
        access = get_project_access(db, user, data.project_id)
        require(access.is_manager and access.is_active, "You cannot create tasks in this project.")

    task = Task(
        task_type=data.task_type,
        title=data.title,
        description=data.description,
        project_id=data.project_id,
        created_by=user.id,
        priority=data.priority,
        due_at=data.due_at,
    )
    db.add(task)
    db.flush()

    if data.task_type == "personal":
        db.add(TaskAssignment(task_id=task.id, assignee_id=user.id, assigned_by=user.id))
    else:
        record_audit(db, user.id, "task.created", "task", task.id, {"project_id": task.project_id})
        if data.assignee_ids:
            _assign(db, user, task, _validate_assignees(db, task.project_id, data.assignee_ids))

    _commit(db)
    db.refresh(task)
    return task


def task_responses(db: Session, user: User, tasks: list[Task], detailed: bool = False) -> list[TaskResponse]:
    if not tasks:
        return []

    ids = [task.id for task in tasks]
    project_ids = {task.project_id for task in tasks if task.project_id}
    titles = dict(
        db.execute(select(Project.id, Project.title).where(Project.id.in_(project_ids))).all()
    ) if project_ids else {}
    managed = set(db.scalars(managed_project_ids(user)).all()) if project_ids else set()

    assignments = db.scalars(
        select(TaskAssignment)
        .options(selectinload(TaskAssignment.assignee))
        .where(TaskAssignment.task_id.in_(ids))
    ).all()
    counts = dict(
        db.execute(
            select(TaskSubmission.assignment_id, func.count())
            .where(TaskSubmission.assignment_id.in_([a.id for a in assignments]))
            .group_by(TaskSubmission.assignment_id)
        ).all()
    ) if assignments else {}

    by_task: dict[UUID, list[TaskAssignment]] = {}
    for assignment in assignments:
        by_task.setdefault(assignment.task_id, []).append(assignment)

    responses = []
    for task in tasks:
        task_assignments = by_task.get(task.id, [])
        can_manage = (
            task.created_by == user.id if task.task_type == "personal" else task.project_id in managed
        )
        mine = next((a for a in task_assignments if a.assignee_id == user.id), None)
        visible = task_assignments if can_manage else ([mine] if mine else [])

        responses.append(
            TaskResponse(
                id=task.id,
                task_type=task.task_type,
                title=task.title,
                description=task.description,
                project_id=task.project_id,
                project_title=titles.get(task.project_id),
                created_by=task.created_by,
                priority=task.priority,
                due_at=task.due_at,
                created_at=task.created_at,
                updated_at=task.updated_at,
                is_overdue=_is_overdue(task, visible),
                my_assignment=_assignment_response(mine, counts.get(mine.id, 0)) if mine else None,
                assignments=[_assignment_response(a, counts.get(a.id, 0)) for a in visible] if detailed or can_manage else [],
                can_manage=can_manage,
            )
        )
    return responses


def list_tasks(
    db: Session,
    user: User,
    params: PageParams,
    scope: str = "all",
    status: str | None = None,
    project_id: UUID | None = None,
    task_type: str | None = None,
    priority: str | None = None,
    overdue: bool = False,
    search: str | None = None,
) -> tuple[list[Task], int]:
    mine = exists().where(TaskAssignment.task_id == Task.id, TaskAssignment.assignee_id == user.id)
    managed = and_(Task.task_type == "official", Task.project_id.in_(managed_project_ids(user)))
    personal = and_(Task.task_type == "personal", Task.created_by == user.id)
    assigned = and_(Task.task_type == "official", mine)

    scopes = {
        "assigned": assigned,
        "personal": personal,
        "mine": or_(assigned, personal),
        "managed": managed,
        "all": or_(assigned, personal, managed),
    }
    if scope not in scopes:
        raise BadRequestError("Invalid task scope.")

    # Archived/deleted projects drop out of ordinary task views except
    # through explicit project filtering.
    statement = (
        select(Task)
        .outerjoin(Project, Project.id == Task.project_id)
        .where(scopes[scope])
        .where(or_(Task.project_id.is_(None), Project.status != "deleted"))
        .order_by(Task.due_at.asc().nulls_last(), Task.created_at.desc())
    )

    if project_id:
        get_project_access(db, user, project_id)
        statement = statement.where(Task.project_id == project_id)
    if task_type:
        statement = statement.where(Task.task_type == task_type)
    if priority:
        statement = statement.where(Task.priority == priority)
    if search and search.strip():
        statement = statement.where(Task.title.ilike(f"%{search.strip()}%"))

    if status:
        # Status belongs to assignments: match my own assignment, or any
        # assignment for tasks I manage.
        statement = statement.where(
            exists().where(
                TaskAssignment.task_id == Task.id,
                TaskAssignment.status == status,
                or_(TaskAssignment.assignee_id == user.id, managed),
            )
        )

    if overdue:
        statement = statement.where(
            Task.due_at < func.now(),
            exists().where(
                TaskAssignment.task_id == Task.id,
                TaskAssignment.status != "completed",
                or_(TaskAssignment.assignee_id == user.id, managed),
            ),
        )

    return paginate(db, statement, params)


def get_task(db: Session, user: User, task_id: UUID) -> Task:
    return _load_context(db, user, task_id).task


def update_task(db: Session, user: User, task_id: UUID, data: TaskUpdate) -> Task:
    context = _load_context(db, user, task_id)
    require(context.can_modify, "You cannot edit this task.")

    task = context.task
    changes = data.model_dump(exclude_unset=True, exclude={"clear_due_at"})
    if data.due_at is not None and data.due_at.tzinfo is None:
        raise BadRequestError("due_at must include a timezone offset.")

    for field, value in changes.items():
        if value is not None:
            setattr(task, field, value.strip() if field == "title" else value)
    if data.clear_due_at:
        task.due_at = None

    if task.task_type == "official":
        record_audit(db, user.id, "task.updated", "task", task.id, {"fields": sorted(changes)})

    _commit(db)
    db.refresh(task)
    return task


def delete_task(db: Session, user: User, task_id: UUID) -> None:
    context = _load_context(db, user, task_id)
    require(context.can_modify, "You cannot delete this task.")

    if context.task.task_type == "official":
        record_audit(db, user.id, "task.deleted", "task", task_id, {"title": context.task.title})
    db.delete(context.task)
    _commit(db)


def add_assignees(db: Session, user: User, task_id: UUID, assignee_ids: list[UUID]) -> Task:
    context = _load_context(db, user, task_id)
    if context.task.task_type != "official":
        raise BadRequestError("Personal tasks cannot be assigned.")
    require(context.can_modify, "You cannot assign this task.")

    _assign(db, user, context.task, _validate_assignees(db, context.task.project_id, assignee_ids))
    _commit(db)
    return context.task


def remove_assignee(db: Session, user: User, task_id: UUID, assignee_id: UUID) -> None:
    context = _load_context(db, user, task_id)
    if context.task.task_type != "official":
        raise BadRequestError("Personal tasks cannot be unassigned.")
    require(context.can_modify, "You cannot change this task's assignees.")

    assignment = db.scalar(
        select(TaskAssignment).where(
            TaskAssignment.task_id == task_id, TaskAssignment.assignee_id == assignee_id
        )
    )
    if not assignment:
        raise NotFoundError("Assignment not found.")

    db.delete(assignment)
    record_audit(db, user.id, "task.unassigned", "task", task_id, {"assignee_id": assignee_id})
    _commit(db)


# --- Workflow -------------------------------------------------------------------------


def change_status(db: Session, user: User, assignment_id: UUID, new_status: str) -> TaskAssignment:
    assignment, context = _load_assignment(db, user, assignment_id)

    if assignment.assignee_id != user.id:
        raise ForbiddenError("Only the assignee can change this status.")
    if context.project_access and not context.project_access.is_active:
        raise ForbiddenError("The project is archived; tasks are read-only.")

    transitions = (
        PERSONAL_TRANSITIONS if context.task.task_type == "personal" else OFFICIAL_ASSIGNEE_TRANSITIONS
    )
    if new_status not in transitions.get(assignment.status, set()):
        raise ConflictError(f"Cannot move a task from {assignment.status} to {new_status}.")

    assignment.status = new_status
    assignment.completed_at = _now() if new_status == "completed" else None

    _commit(db)
    db.refresh(assignment)
    return assignment


def submit(db: Session, user: User, assignment_id: UUID, data: SubmissionCreate) -> TaskSubmission:
    assignment, context = _load_assignment(db, user, assignment_id)

    if context.task.task_type != "official":
        raise BadRequestError("Personal tasks do not take submissions.")
    if assignment.assignee_id != user.id:
        raise ForbiddenError("Only the assignee can submit work.")
    if not context.project_access.is_active:
        raise ForbiddenError("The project is archived; tasks are read-only.")

    # Lock the assignment so concurrent submissions get distinct versions.
    db.execute(select(TaskAssignment).where(TaskAssignment.id == assignment.id).with_for_update())
    if assignment.status not in SUBMITTABLE_STATUSES:
        raise ConflictError(
            "This task is already under review or completed."
            if assignment.status in ("under_review", "completed")
            else "This task cannot be submitted now."
        )

    version = (
        db.scalar(
            select(func.max(TaskSubmission.version)).where(TaskSubmission.assignment_id == assignment.id)
        )
        or 0
    ) + 1

    submission = TaskSubmission(
        assignment_id=assignment.id,
        version=version,
        response_text=data.response_text.strip(),
        links=[str(link) for link in data.links],
        submitted_by=user.id,
    )
    db.add(submission)

    assignment.status = "under_review"
    assignment.submitted_at = _now()

    reviewers = db.scalars(
        select(ProjectMember.user_id).where(
            ProjectMember.project_id == context.task.project_id,
            ProjectMember.membership_status == "active",
            ProjectMember.membership_role.in_(("supervisor", "owner")),
            ProjectMember.user_id != user.id,
        )
    ).all()
    for reviewer_id in reviewers:
        enqueue_notification(
            db,
            recipient_id=reviewer_id,
            category="tasks",
            event_type="task.submitted",
            title="Task submission received",
            body=f"{user.full_name} submitted version {version} of “{context.task.title}”.",
            entity_type="task",
            entity_id=context.task.id,
            dedupe_key=f"task.submitted:{assignment.id}:{version}:{reviewer_id}",
        )

    _commit(db)
    db.refresh(submission)
    return submission


def list_submissions(db: Session, user: User, assignment_id: UUID) -> list[TaskSubmission]:
    assignment, _ = _load_assignment(db, user, assignment_id)
    return list(
        db.scalars(
            select(TaskSubmission)
            .options(selectinload(TaskSubmission.reviews))
            .where(TaskSubmission.assignment_id == assignment.id)
            .order_by(TaskSubmission.version.desc())
        ).all()
    )


def review(db: Session, user: User, submission_id: UUID, decision: str, feedback: str) -> TaskReview:
    submission = db.get(TaskSubmission, submission_id)
    if not submission:
        raise NotFoundError("Submission not found.")

    assignment, context = _load_assignment(db, user, submission.assignment_id)
    require(
        context.task.task_type == "official" and context.project_access.is_manager,
        "Only project supervisors can review submissions.",
    )
    if assignment.assignee_id == user.id:
        raise ForbiddenError("You cannot review your own submission.")
    if not context.project_access.is_active:
        raise ForbiddenError("The project is archived; tasks are read-only.")
    if assignment.status != "under_review":
        raise ConflictError("Only submissions under review can be reviewed.")

    latest = db.scalar(
        select(func.max(TaskSubmission.version)).where(TaskSubmission.assignment_id == assignment.id)
    )
    if submission.version != latest:
        raise ConflictError("Only the latest submission version can be reviewed.")

    task_review = TaskReview(
        submission_id=submission.id,
        reviewer_id=user.id,
        decision=decision,
        feedback=feedback.strip(),
    )
    db.add(task_review)

    if decision == "approved":
        assignment.status = "completed"
        assignment.completed_at = _now()
    else:
        assignment.status = "revision_required"

    record_audit(
        db, user.id, "task.reviewed", "task", context.task.id,
        {"assignment_id": assignment.id, "version": submission.version, "decision": decision},
    )
    enqueue_notification(
        db,
        recipient_id=assignment.assignee_id,
        category="tasks",
        event_type="task.reviewed",
        title="Task reviewed",
        body=f"Your submission for “{context.task.title}” was "
        + ("approved." if decision == "approved" else "returned for revision."),
        entity_type="task",
        entity_id=context.task.id,
        dedupe_key=f"task.reviewed:{submission.id}",
    )

    _commit(db)
    db.refresh(task_review)
    return task_review


def pending_reviews(db: Session, user: User, params: PageParams, project_id: UUID | None = None):
    statement = (
        select(TaskAssignment, Task, Project.title)
        .join(Task, Task.id == TaskAssignment.task_id)
        .join(Project, Project.id == Task.project_id)
        .options(selectinload(TaskAssignment.assignee))
        .where(
            Task.task_type == "official",
            TaskAssignment.status == "under_review",
            Task.project_id.in_(managed_project_ids(user)),
            TaskAssignment.assignee_id != user.id,
        )
        .order_by(TaskAssignment.submitted_at.asc())
    )
    if project_id:
        statement = statement.where(Task.project_id == project_id)
    rows, total = paginate(db, statement, params, scalars=False)

    latest = {}
    if rows:
        for assignment_id, submission_id, version in db.execute(
            select(TaskSubmission.assignment_id, TaskSubmission.id, TaskSubmission.version)
            .where(TaskSubmission.assignment_id.in_([row[0].id for row in rows]))
            .order_by(TaskSubmission.version)
        ).all():
            latest[assignment_id] = (submission_id, version)
    return rows, total, latest


def submission_response(db: Session, submission: TaskSubmission) -> SubmissionResponse:
    reviewer_ids = {r.reviewer_id for r in submission.reviews if r.reviewer_id}
    reviewers = {u.id: u for u in db.scalars(select(User).where(User.id.in_(reviewer_ids))).all()} if reviewer_ids else {}
    return SubmissionResponse(
        id=submission.id,
        assignment_id=submission.assignment_id,
        version=submission.version,
        response_text=submission.response_text,
        links=submission.links,
        submitted_at=submission.submitted_at,
        reviews=[
            ReviewResponse(
                id=r.id,
                reviewer=user_summary(reviewers[r.reviewer_id]) if r.reviewer_id in reviewers else None,
                decision=r.decision,
                feedback=r.feedback,
                created_at=r.created_at,
            )
            for r in submission.reviews
        ],
    )
