import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# https://github.com/<owner>/<repo>[/more/path]; owner rules follow GitHub's
# (alphanumeric or single hyphens, max 39 chars).
_GITHUB_REPO = re.compile(
    r"^https://github\.com/"
    r"(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38})/"
    r"(?P<repo>[A-Za-z0-9._-]{1,100})"
    r"(?P<rest>(?:/[A-Za-z0-9._~%@+=-]+)*)$"
)


def normalize_github_url(value: str) -> str:
    url = value.strip()
    if url.lower().startswith("https://www.github.com/"):
        url = "https://github.com/" + url[len("https://www.github.com/"):]
    url = url.split("#", 1)[0].split("?", 1)[0].rstrip("/")
    match = _GITHUB_REPO.match(url)
    if not match or match.group("repo") in (".", ".."):
        raise ValueError("Enter a GitHub repository link like https://github.com/owner/repository.")
    if not match.group("rest") and url.endswith(".git"):
        url = url[: -len(".git")]
    return url


class RepoLinkCreate(BaseModel):
    url: str = Field(max_length=500)
    label: str | None = Field(default=None, max_length=100)

    @field_validator("url")
    @classmethod
    def _valid_github(cls, value: str) -> str:
        return normalize_github_url(value)

    @field_validator("label")
    @classmethod
    def _clean_label(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class RepoLinkResponse(BaseModel):
    id: UUID
    project_id: UUID
    url: str
    label: str | None
    added_by: UUID | None
    added_by_username: str | None = None
    created_at: datetime
    can_remove: bool = False
