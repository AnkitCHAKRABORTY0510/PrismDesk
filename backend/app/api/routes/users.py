from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_role
from app.core.permissions import ADMINISTRATOR, PROFESSOR
from app.database.session import get_db
from app.models.role import Role
from app.models.user import User
from app.schemas.admin import RoleName, UserSummary, user_summary

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/directory", response_model=list[UserSummary])
def user_directory(
    search: str | None = Query(default=None, max_length=100),
    role_name: RoleName | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    _: User = Depends(require_role(ADMINISTRATOR, PROFESSOR)),
):
    """Approved users for membership and assignment pickers.

    Only people who manage projects can search the directory, and it
    exposes no email addresses or account metadata.
    """

    statement = (
        select(User)
        .where(User.account_status == "approved")
        .order_by(User.full_name)
        .limit(limit)
    )

    if search and search.strip():
        term = f"%{search.strip()}%"
        statement = statement.where(
            or_(User.username.ilike(term), User.full_name.ilike(term))
        )

    if role_name:
        statement = statement.where(User.roles.any(Role.name == role_name))

    return [user_summary(user) for user in db.scalars(statement).all()]
