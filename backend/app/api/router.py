from fastapi import APIRouter

from app.api.routes.admin import router as admin_router
from app.api.routes.audit import router as audit_router
from app.api.routes.auth import router as auth_router
from app.api.routes.conferences import router as conferences_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.handbook import router as handbook_router
from app.api.routes.journals import router as journals_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.project_links import router as project_links_router
from app.api.routes.projects import router as projects_router
from app.api.routes.research import router as research_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.users import router as users_router

api_router = APIRouter(
    prefix="/api/v1",
)

api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(users_router)
api_router.include_router(audit_router)
api_router.include_router(projects_router)
api_router.include_router(project_links_router)
api_router.include_router(research_router)
api_router.include_router(tasks_router)
api_router.include_router(handbook_router)
api_router.include_router(conferences_router)
api_router.include_router(journals_router)
api_router.include_router(notifications_router)
api_router.include_router(dashboard_router)
