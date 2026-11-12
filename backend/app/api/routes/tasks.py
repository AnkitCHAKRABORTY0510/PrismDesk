from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, page_params
from app.database.session import get_db
from app.models.user import User
from app.schemas.admin import user_summary
from app.schemas.common import MessageResponse, Page, PageParams
from app.schemas.task import (
    AssigneesRequest,
    AssignmentResponse,
    AssignmentStatus,
    PendingReviewResponse,
    ReminderRecipient,
    ReviewCreate,
    SubmissionCreate,
    SubmissionResponse,
    StatusUpdate,
    TaskCreate,
    TaskPriority,
    TaskResponse,
    TaskType,
    TaskUpdate,
)
from app.services import task_service

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def _detail(db, user, task) -> TaskResponse:
    return task_service.task_responses(db, user, [task], detailed=True)[0]


@router.get("", response_model=Page[TaskResponse])
def list_tasks(
    scope: Literal["all", "mine", "assigned", "personal", "managed", "reminders"] = "all",
    status_filter: AssignmentStatus | None = Query(default=None, alias="status"),
    project_id: UUID | None = None,
    task_type: TaskType | None = None,
    priority: TaskPriority | None = None,
    overdue: bool = False,
    search: str | None = Query(default=None, max_length=200),
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tasks, total = task_service.list_tasks(
        db, user, params, scope, status_filter, project_id, task_type, priority, overdue, search
    )
    return Page(
        items=task_service.task_responses(db, user, tasks),
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(data: TaskCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _detail(db, user, task_service.create_task(db, user, data))


@router.get("/reminder-recipients", response_model=list[ReminderRecipient])
def reminder_recipients(
    project_id: UUID | None = None,
    related_task_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Who the caller may remind in a project (or about a task)."""

    return [
        ReminderRecipient(user=user_summary(member), membership_role=role)
        for member, role in task_service.reminder_recipients(db, user, project_id, related_task_id)
    ]


@router.get("/reviews/pending", response_model=Page[PendingReviewResponse])
def pending_reviews(
    project_id: UUID | None = None,
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows, total, latest = task_service.pending_reviews(db, user, params, project_id)
    items = []
    for assignment, task, project_title in rows:
        submission_id, version = latest.get(assignment.id, (None, None))
        items.append(
            PendingReviewResponse(
                assignment=task_service._assignment_response(assignment),
                task_id=task.id,
                task_title=task.title,
                project_id=task.project_id,
                project_title=project_title,
                latest_submission_id=submission_id,
                latest_version=version,
                submitted_at=assignment.submitted_at,
            )
        )
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _detail(db, user, task_service.get_task(db, user, task_id))


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: UUID, data: TaskUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return _detail(db, user, task_service.update_task(db, user, task_id, data))


@router.delete("/{task_id}", response_model=MessageResponse)
def delete_task(task_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task_service.delete_task(db, user, task_id)
    return MessageResponse(message="Task deleted.")


@router.post("/{task_id}/assignees", response_model=TaskResponse)
def add_assignees(
    task_id: UUID,
    data: AssigneesRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _detail(db, user, task_service.add_assignees(db, user, task_id, data.assignee_ids))


@router.delete("/{task_id}/assignees/{assignee_id}", response_model=MessageResponse)
def remove_assignee(
    task_id: UUID, assignee_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    task_service.remove_assignee(db, user, task_id, assignee_id)
    return MessageResponse(message="Assignee removed.")


@router.patch("/assignments/{assignment_id}/status", response_model=AssignmentResponse)
def change_status(
    assignment_id: UUID,
    data: StatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return task_service._assignment_response(task_service.change_status(db, user, assignment_id, data.status))


@router.get("/assignments/{assignment_id}/submissions", response_model=list[SubmissionResponse])
def list_submissions(
    assignment_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return [
        task_service.submission_response(db, submission)
        for submission in task_service.list_submissions(db, user, assignment_id)
    ]


@router.post(
    "/assignments/{assignment_id}/submissions",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit(
    assignment_id: UUID,
    data: SubmissionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return task_service.submission_response(db, task_service.submit(db, user, assignment_id, data))


@router.post("/submissions/{submission_id}/review", response_model=SubmissionResponse)
def review_submission(
    submission_id: UUID,
    data: ReviewCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task_review = task_service.review(db, user, submission_id, data.decision, data.feedback)
    db.refresh(task_review.submission)
    return task_service.submission_response(db, task_review.submission)
