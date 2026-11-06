from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: UUID
    actor_user_id: UUID | None
    actor_username: str | None = None
    action: str
    entity_type: str
    entity_id: str | None
    details: dict
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
