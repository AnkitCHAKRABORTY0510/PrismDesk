from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        raise ValueError("Timestamps must include a timezone offset.")
    return value


class ImportantDate(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    date: datetime

    _aware = field_validator("date")(_aware)


class ConferenceBase(BaseModel):
    name: str = Field(min_length=2, max_length=300)
    acronym: str | None = Field(default=None, max_length=50)
    website_url: HttpUrl | None = None
    cfp_url: HttpUrl | None = None
    submission_deadline: datetime
    important_dates: list[ImportantDate] = Field(default_factory=list, max_length=20)
    location: str | None = Field(default=None, max_length=200)
    notes: str = Field(default="", max_length=5000)

    _aware = field_validator("submission_deadline")(_aware)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Conference name is too short.")
        return value


class ConferenceCreate(ConferenceBase):
    project_id: UUID | None = None


class ConferenceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=300)
    acronym: str | None = Field(default=None, max_length=50)
    website_url: HttpUrl | None = None
    cfp_url: HttpUrl | None = None
    submission_deadline: datetime | None = None
    important_dates: list[ImportantDate] | None = Field(default=None, max_length=20)
    location: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=5000)

    _aware = field_validator("submission_deadline")(_aware)


class ConferenceProjectLink(BaseModel):
    project_id: UUID
    project_title: str
    status: Literal["active", "archived"]
    added_at: datetime
    can_manage: bool = False


class ConferenceResponse(BaseModel):
    id: UUID
    name: str
    acronym: str | None
    website_url: str | None
    cfp_url: str | None
    submission_deadline: datetime
    important_dates: list[dict]
    location: str | None
    notes: str
    added_by: UUID | None
    created_at: datetime
    updated_at: datetime
    is_overdue: bool
    seconds_remaining: int
    projects: list[ConferenceProjectLink] = []
    can_edit: bool = False
    linked_existing: bool = False


class ConferenceLinkRequest(BaseModel):
    project_id: UUID
