from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_capability
from app.core.config import settings
from app.database.session import get_db
from app.models.user import User
from app.schemas.dashboard import (
    AdminDashboard,
    GuestDashboard,
    ProfessorDashboard,
    ProjectAnalytics,
    StudentDashboard,
)
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboards"])


@router.get("/admin", response_model=AdminDashboard)
def admin_dashboard(db: Session = Depends(get_db), _: User = Depends(require_capability("dashboard.admin"))):
    return dashboard_service.admin_dashboard(db)


@router.get("/professor", response_model=ProfessorDashboard)
def professor_dashboard(
    db: Session = Depends(get_db), user: User = Depends(require_capability("dashboard.professor"))
):
    return dashboard_service.professor_dashboard(db, user)


@router.get("/student", response_model=StudentDashboard)
def student_dashboard(db: Session = Depends(get_db), user: User = Depends(require_capability("dashboard.student"))):
    return dashboard_service.student_dashboard(db, user)


@router.get("/guest", response_model=GuestDashboard)
def guest_dashboard(db: Session = Depends(get_db), user: User = Depends(require_capability("dashboard.guest"))):
    return dashboard_service.guest_dashboard(db, user)


@router.get("/projects/{project_id}", response_model=ProjectAnalytics)
def project_analytics(project_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return dashboard_service.project_analytics(db, user, project_id)


@router.get("/system-settings")
def system_settings(_: User = Depends(require_capability("settings.view"))):
    """Non-secret configuration summary for administrators."""

    return {
        "environment": settings.APP_ENV,
        "session_expire_hours": settings.SESSION_EXPIRE_HOURS,
        "session_inactivity_minutes": settings.SESSION_INACTIVITY_MINUTES,
        "secure_cookies": settings.cookie_secure,
        "cors_origins": settings.cors_origin_list,
        "rate_limiting": settings.RATE_LIMIT_ENABLED,
        "project_delete_retention_days": settings.PROJECT_DELETE_RETENTION_DAYS,
        "discord_oauth_configured": settings.discord_oauth_configured,
        "discord_bot_configured": settings.discord_bot_configured,
        "discord_announcement_channel_configured": bool(settings.DISCORD_ANNOUNCEMENT_CHANNEL_ID),
        "notification_max_attempts": settings.NOTIFICATION_MAX_ATTEMPTS,
        "task_reminder_hours": settings.TASK_REMINDER_HOURS,
        "conference_reminder_days": settings.CONFERENCE_REMINDER_DAYS,
    }
