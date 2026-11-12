import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator

_ISSN = re.compile(r"^\d{4}-?\d{3}[\dXx]$")


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        raise ValueError("Timestamps must include a timezone offset.")
    return value


def _issn(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    value = value.strip().upper()
    if not _ISSN.match(value):
        raise ValueError("ISSN must look like 1234-567X.")
    return value if "-" in value else f"{value[:4]}-{value[4:]}"


class JournalBase(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    issn: str | None = Field(default=None, max_length=9)
    publisher: str | None = Field(default=None, max_length=300)
    homepage_url: HttpUrl | None = None
    sjr_quartile: Literal["Q1", "Q2", "Q3", "Q4"] | None = None
    sjr: float | None = Field(default=None, ge=0)
    h_index: int | None = Field(default=None, ge=0)
    subject_areas: list[str] = Field(default_factory=list, max_length=20)
    is_open_access: bool = False
    notes: str = Field(default="", max_length=5000)
    special_issue_title: str | None = Field(default=None, max_length=300)
    submission_deadline: datetime | None = None
    project_id: UUID | None = None

    _aware = field_validator("submission_deadline")(_aware)
    _issn = field_validator("issn")(_issn)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Journal title is too short.")
        return value


class JournalCreate(JournalBase):
    pass


class JournalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=300)
    issn: str | None = Field(default=None, max_length=9)
    publisher: str | None = Field(default=None, max_length=300)
    homepage_url: HttpUrl | None = None
    sjr_quartile: Literal["Q1", "Q2", "Q3", "Q4"] | None = None
    sjr: float | None = Field(default=None, ge=0)
    h_index: int | None = Field(default=None, ge=0)
    subject_areas: list[str] | None = Field(default=None, max_length=20)
    is_open_access: bool | None = None
    notes: str | None = Field(default=None, max_length=5000)
    special_issue_title: str | None = Field(default=None, max_length=300)
    submission_deadline: datetime | None = None
    project_id: UUID | None = None

    _aware = field_validator("submission_deadline")(_aware)
    _issn = field_validator("issn")(_issn)


class JournalResponse(BaseModel):
    id: UUID
    title: str
    issn: str | None
    publisher: str | None
    homepage_url: str | None
    sjr_quartile: str | None
    sjr: float | None
    h_index: int | None
    subject_areas: list[str]
    is_open_access: bool
    notes: str
    special_issue_title: str | None
    submission_deadline: datetime | None
    project_id: UUID | None
    project_title: str | None = None
    created_at: datetime
    updated_at: datetime
    is_overdue: bool
    seconds_remaining: int | None
    wikicfp_url: str
    google_special_issues_url: str
    linked_existing: bool = False


# --- Browse catalog -----------------------------------------------------------


class JournalCategory(BaseModel):
    name: str
    quartile: str | None


class JournalCatalogItem(BaseModel):
    issn: str | None
    issns: list[str]
    title: str
    publisher: str | None
    homepage_url: str | None
    areas: list[str]
    domains: list[str]
    categories: list[JournalCategory]
    sjr: float | None
    sjr_quartile: str | None
    sjr_rank: int | None
    h_index: int | None
    country: str | None
    two_year_mean_citedness: float | None
    works_count: int | None
    cited_by_count: int | None
    is_oa: bool
    is_in_doaj: bool
    apc_usd: int | None
    openalex_id: str | None
    openalex_url: str | None
    sjr_url: str | None
    enriched: bool
    submission_mode: Literal["rolling"]
    wikicfp_url: str
    google_special_issues_url: str
    in_my_list: bool = False
    my_journal_id: UUID | None = None


class JournalCatalogSource(BaseModel):
    name: str
    url: str
    license: str
    available: bool
    fetched_at: datetime | None = None
    stale: bool = False
    note: str | None = None


class JournalDomain(BaseModel):
    id: str
    label: str


class JournalCatalogResponse(BaseModel):
    items: list[JournalCatalogItem]
    total: int
    total_is_estimate: bool
    limit: int
    offset: int
    mode: Literal["sjr", "openalex"]
    ranking_available: bool
    ranking: JournalCatalogSource
    metadata: JournalCatalogSource
    domains: list[JournalDomain]


class JournalCatalogRefreshResponse(BaseModel):
    ranking_available: bool
    total: int
    fetched_at: datetime | None
    stale: bool
    note: str | None = None


class JournalCatalogAddRequest(BaseModel):
    project_id: UUID | None = None
