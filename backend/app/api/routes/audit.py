from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import page_params, require_capability
from app.database.session import get_db
from app.models.user import User
from app.schemas.audit import AuditLogResponse
from app.schemas.common import Page, PageParams
from app.services.audit_service import list_audit_logs

router = APIRouter(prefix="/audit", tags=["Audit"])


# Audit logs are read-only through the API; there are no write routes.
@router.get("/logs", response_model=Page[AuditLogResponse])
def get_audit_logs(
    action: str | None = Query(default=None, max_length=80),
    entity_type: str | None = Query(default=None, max_length=50),
    actor_id: UUID | None = None,
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: User = Depends(require_capability("audit.view")),
):
    logs, total = list_audit_logs(db, params, action, entity_type, actor_id)

    actor_ids = {log.actor_user_id for log in logs if log.actor_user_id}
    usernames = dict(
        db.execute(
            select(User.id, User.username).where(User.id.in_(actor_ids))
        ).all()
    ) if actor_ids else {}

    items = []
    for log in logs:
        item = AuditLogResponse.model_validate(log)
        item.actor_username = usernames.get(log.actor_user_id)
        items.append(item)

    return Page(items=items, total=total, page=params.page, page_size=params.page_size)
