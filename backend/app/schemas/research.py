import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator

ReadingStatus = Literal["not_started", "reading", "completed"]

_DOI_PREFIX = re.compile(r"^(https?://(dx\.)?doi\.org/|doi:)", re.IGNORECASE)
_DOI_SHAPE = re.compile(r"^10\.\d{4,9}/\S+$")


def normalize_doi(value: str | None) -> str | None:
    if value is None:
        return None
    value = _DOI_PREFIX.sub("", value.strip()).strip().lower()
    if not value:
        return None
    if not _DOI_SHAPE.match(value):
        raise ValueError("DOI must look like 10.xxxx/identifier.")
    return value


def _clean_list(values: list[str] | None) -> list[str]:
    seen: list[str] = []
    for item in values or []:
        item = item.strip()
        if item and item.lower() not in {existing.lower() for existing in seen}:
            seen.append(item)
    return seen


class PaperBase(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    authors: list[str] = Field(default_factory=list, max_length=100)
    abstract: str = Field(default="", max_length=20000)
    publication_year: int | None = Field(default=None, ge=1800, le=2200)
    venue: str | None = Field(default=None, max_length=300)
    doi: str | None = Field(default=None, max_length=255)
    url: HttpUrl | None = None
    keywords: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be empty.")
        return value

    @field_validator("authors", "keywords")
    @classmethod
    def clean_lists(cls, value: list[str]) -> list[str]:
        cleaned = _clean_list(value)
        if any(len(item) > 200 for item in cleaned):
            raise ValueError("List items must be at most 200 characters.")
        return cleaned

    @field_validator("doi")
    @classmethod
    def validate_doi(cls, value: str | None) -> str | None:
        return normalize_doi(value)

    @field_validator("venue")
    @classmethod
    def strip_venue(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None


class PaperCreate(PaperBase):
    project_id: UUID | None = Field(
        default=None,
        description="Optionally link the paper to this project. If a paper "
        "with the same DOI exists it is linked instead of duplicated.",
    )


class PaperUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    authors: list[str] | None = Field(default=None, max_length=100)
    abstract: str | None = Field(default=None, max_length=20000)
    publication_year: int | None = Field(default=None, ge=1800, le=2200)
    venue: str | None = Field(default=None, max_length=300)
    doi: str | None = Field(default=None, max_length=255)
    url: HttpUrl | None = None
    keywords: list[str] | None = Field(default=None, max_length=50)

    @field_validator("authors", "keywords")
    @classmethod
    def clean_lists(cls, value: list[str] | None) -> list[str] | None:
        return _clean_list(value) if value is not None else None

    @field_validator("doi")
    @classmethod
    def validate_doi(cls, value: str | None) -> str | None:
        return normalize_doi(value)


class LinkedProject(BaseModel):
    id: UUID
    title: str


class PaperResponse(BaseModel):
    id: UUID
    title: str
    authors: list[str]
    abstract: str
    publication_year: int | None
    venue: str | None
    doi: str | None
    url: str | None
    keywords: list[str]
    added_by: UUID | None
    created_at: datetime
    updated_at: datetime
    projects: list[LinkedProject] = []
    my_status: ReadingStatus | None = None
    can_edit: bool = False
    linked_existing: bool = False
    discord_thread_url: str | None = None


class DoiLookupResponse(BaseModel):
    """Metadata suggested for a DOI, arXiv ID, link or title.

    Nothing is stored until the user saves the paper form.
    """

    title: str | None = None
    authors: list[str] = []
    abstract: str = ""
    publication_year: int | None = None
    venue: str | None = None
    doi: str | None = None
    url: str | None = None
    keywords: list[str] = []
    existing_paper_id: UUID | None = None
    matched_by: Literal["doi", "arxiv", "url", "title"] | None = Field(
        default=None, description="What the query was recognised as."
    )
    source: str | None = Field(
        default=None, description="Where the metadata came from, e.g. crossref, arxiv, webpage+crossref."
    )


class ProjectLinkRequest(BaseModel):
    project_id: UUID


class ReadingProgressUpdate(BaseModel):
    status: ReadingStatus
    project_id: UUID | None = None


class ReadingProgressResponse(BaseModel):
    paper_id: UUID
    paper_title: str | None = None
    project_id: UUID | None
    user_id: UUID
    username: str | None = None
    status: ReadingStatus
    updated_at: datetime


class NoteCreate(BaseModel):
    content: str = Field(min_length=1, max_length=20000)
    project_id: UUID | None = None


class NoteUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=20000)


class NoteResponse(BaseModel):
    id: UUID
    paper_id: UUID
    project_id: UUID | None
    content: str
    created_at: datetime
    updated_at: datetime
