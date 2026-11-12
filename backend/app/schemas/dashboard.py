from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class CountMap(BaseModel):
    """Counts keyed by status; missing statuses are zero."""

    counts: dict[str, int]
    total: int


class DeadlineItem(BaseModel):
    id: UUID
    title: str
    due_at: datetime
    kind: str  # "task" | "conference"
    project_id: UUID | None = None
    project_title: str | None = None
    status: str | None = None


class ActivityItem(BaseModel):
    id: UUID
    action: str
    entity_type: str
    entity_id: str | None
    actor_username: str | None
    created_at: datetime


class MemberChip(BaseModel):
    user_id: UUID
    username: str
    full_name: str
    membership_role: str


class RepoLinkChip(BaseModel):
    url: str
    label: str | None = None


class ProjectSummaryItem(BaseModel):
    id: UUID
    title: str
    status: str
    my_role: str | None = None
    member_count: int = 0
    assignments_total: int = 0
    assignments_completed: int = 0
    pending_reviews: int = 0
    overdue: int = 0
    # Official assignment counts by status (per-project pipeline).
    assignment_counts: dict[str, int] = {}
    # First few active members, for avatar stacks.
    members: list[MemberChip] = []
    repo_links: list[RepoLinkChip] = []

    @property
    def completion_rate(self) -> float:
        return self.assignments_completed / self.assignments_total if self.assignments_total else 0.0


class HandbookItem(BaseModel):
    id: UUID
    entry_date: date
    student_username: str
    project_id: UUID
    project_title: str
    comment_count: int = 0


class ReviewItem(BaseModel):
    assignment_id: UUID
    task_id: UUID
    task_title: str
    student_username: str
    project_title: str
    submitted_at: datetime | None


class ReadingListItem(BaseModel):
    paper_id: UUID
    title: str
    venue: str | None = None
    publication_year: int | None = None
    status: str  # not_started | reading | completed


class MemberReading(BaseModel):
    user_id: UUID
    username: str
    full_name: str
    counts: dict[str, int]
    total: int


class DayCount(BaseModel):
    day: date
    count: int


class AdminDashboard(BaseModel):
    users: CountMap
    projects: CountMap
    research_papers: int
    tasks: CountMap
    overdue_assignments: int
    notifications: CountMap
    upcoming_conferences: list[DeadlineItem]
    recent_activity: list[ActivityItem]
    my_reading: CountMap = CountMap(counts={}, total=0)
    reading_list: list[ReadingListItem] = []


class ProfessorDashboard(BaseModel):
    supervised_projects: list[ProjectSummaryItem]
    member_count: int
    pending_reviews: int
    review_queue: list[ReviewItem]
    recent_handbook_entries: list[HandbookItem]
    upcoming_deadlines: list[DeadlineItem]
    reading_progress: CountMap
    my_reading: CountMap = CountMap(counts={}, total=0)
    reading_list: list[ReadingListItem] = []
    member_reading: list[MemberReading] = []
    open_reminders: int = 0


class StudentDashboard(BaseModel):
    joined_projects: list[ProjectSummaryItem]
    owned_project_count: int
    assigned_tasks: CountMap
    personal_tasks: CountMap
    pending_submissions: int
    task_completion_rate: float
    reading_progress: CountMap
    handbook_entries_last_7_days: int
    handbook_entries_last_30_days: int
    recent_handbook_entries: list[HandbookItem]
    upcoming_deadlines: list[DeadlineItem]
    reading_list: list[ReadingListItem] = []
    # Handbook entries per day for the activity heatmap (last 12 weeks).
    handbook_days: list[DayCount] = []
    handbook_streak: int = 0
    open_reminders: int = 0


class GuestDashboard(BaseModel):
    projects: list[ProjectSummaryItem]
    paper_count: int
    upcoming_conferences: list[DeadlineItem]


class WeeklyCount(BaseModel):
    week_start: date
    count: int


class ProjectAnalytics(BaseModel):
    project_id: UUID
    assignments: CountMap
    completion_rate: float
    overdue_assignments: int
    reading_progress: CountMap
    paper_count: int
    handbook_per_week: list[WeeklyCount]
    activity_last_30_days: int
    upcoming_deadlines: list[DeadlineItem]
