"""Audit trail helpers.

Audit rows are added to the caller's transaction so the record is
committed (or rolled back) together with the action it describes.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.schemas.common import PageParams, paginate

# Keys that must never reach the audit trail, even by accident.
_FORBIDDEN_KEY_PARTS = (
    "password",
    "token",
    "secret",
    "note",
    "content",
    "body",
    "response",
)


def _sanitize(details: dict | None) -> dict:
    if not details:
        return {}

    clean = {}

    for key, value in details.items():
        if any(part in key.lower() for part in _FORBIDDEN_KEY_PARTS):
            continue

        if isinstance(value, UUID):
            value = str(value)
        elif isinstance(value, (list, tuple, set)):
            value = [str(item) if isinstance(item, UUID) else item for item in value]

        clean[key] = value

    return clean


def record_audit(
    db: Session,
    actor_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: UUID | str | None = None,
    details: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_user_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        details=_sanitize(details),
    )
    db.add(entry)
    return entry


def list_audit_logs(
    db: Session,
    params: PageParams,
    action: str | None = None,
    entity_type: str | None = None,
    actor_id: UUID | None = None,
) -> tuple[list[AuditLog], int]:
    statement = select(AuditLog).order_by(AuditLog.created_at.desc())

    if action:
        statement = statement.where(AuditLog.action == action)
    if entity_type:
        statement = statement.where(AuditLog.entity_type == entity_type)
    if actor_id:
        statement = statement.where(AuditLog.actor_user_id == actor_id)

    return paginate(db, statement, params)
