from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

Category = Literal["tasks", "projects", "conferences", "handbook", "administrative"]
NotificationStatus = Literal["pending", "processing", "sent", "failed", "retry_scheduled"]


class DiscordStatusResponse(BaseModel):
    linked: bool
    discord_username: str | None = None
    linked_at: datetime | None = None
    oauth_configured: bool
    bot_configured: bool


class DiscordLinkStartResponse(BaseModel):
    authorize_url: str


class PreferenceItem(BaseModel):
    category: Category
    enabled: bool


class PreferencesUpdate(BaseModel):
    preferences: list[PreferenceItem] = Field(min_length=1, max_length=10)


class NotificationResponse(BaseModel):
    id: UUID
    recipient_id: UUID | None
    channel_id: str | None
    category: str
    event_type: str
    title: str
    body: str
    status: NotificationStatus
    attempt_count: int
    max_attempts: int
    next_attempt_at: datetime
    last_attempt_at: datetime | None
    sent_at: datetime | None
    last_error: str | None
    created_at: datetime


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=1800)
    post_to_channel: bool = True
    direct_message_all: bool = False

    @model_validator(mode="after")
    def has_destination(self):
        if not (self.post_to_channel or self.direct_message_all):
            raise ValueError("Choose at least one destination.")
        return self


class AnnouncementResponse(BaseModel):
    queued: int
    channel_configured: bool
