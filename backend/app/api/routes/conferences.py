from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, page_params
from app.core.errors import NotFoundError
from app.database.session import get_db
from app.models.user import User
from app.schemas.common import MessageResponse, Page, PageParams
from app.schemas.conference import (
    CatalogAddRequest,
    CatalogCategory,
    CatalogItem,
    CatalogRefreshResponse,
    CatalogResponse,
    CatalogSource,
    CatalogTopic,
    ConferenceCreate,
    ConferenceLinkRequest,
    ConferenceResponse,
    ConferenceUpdate,
)
from app.services import conference_catalog, conference_service

router = APIRouter(prefix="/conferences", tags=["Conferences"])


def _one(db, user, conference) -> ConferenceResponse:
    return conference_service.conference_responses(db, user, [conference])[0]


@router.get("", response_model=Page[ConferenceResponse])
def list_conferences(
    search: str | None = Query(default=None, max_length=200),
    project_id: UUID | None = None,
    deadline_from: datetime | None = None,
    deadline_to: datetime | None = None,
    timing: Literal["upcoming", "overdue"] | None = None,
    include_archived_links: bool = False,
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conferences, total = conference_service.list_conferences(
        db, user, params, search, project_id, deadline_from, deadline_to, timing, include_archived_links
    )
    return Page(
        items=conference_service.conference_responses(db, user, conferences),
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post("", response_model=ConferenceResponse, status_code=status.HTTP_201_CREATED)
def create_conference(
    data: ConferenceCreate,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conference, linked_existing = conference_service.create_conference(db, user, data)
    result = _one(db, user, conference)
    result.linked_existing = linked_existing
    if linked_existing:
        response.status_code = status.HTTP_200_OK
    return result


# --- Browse catalog (declared before "/{conference_id}" so paths match) ---


@router.get("/catalog", response_model=CatalogResponse)
def browse_catalog(
    q: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None, max_length=10),
    core_rank: str | None = Query(default=None, max_length=10),
    ccf_rank: str | None = Query(default=None, max_length=10),
    upcoming_only: bool = True,
    sort: Literal["deadline", "name"] = "deadline",
    topic: str | None = Query(
        default=None,
        pattern="^(prism|architecture|embedded|vlsi|low_power|reliability|security|ai|systems)$",
        description='A topic tag, or "prism" for the PRISM focus preset.',
    ),
    scope: Literal["lab", "all"] = "lab",
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    snapshot = conference_catalog.get_catalog()
    now = datetime.now(timezone.utc)
    views = conference_catalog.filter_and_sort(
        [conference_catalog.catalog_view(c, now) for c in snapshot.conferences],
        q=q,
        category=category,
        core_rank=core_rank,
        ccf_rank=ccf_rank,
        upcoming_only=upcoming_only,
        sort=sort,
        topic=topic,
        scope=scope,
    )
    page = views[offset : offset + limit]
    matches = conference_service.catalog_matches(
        db, user, [conference_service.catalog_conference_name(v) for v in page]
    )
    items = []
    for view in page:
        match = matches.get(conference_service.catalog_conference_name(view).lower())
        items.append(CatalogItem(**view, in_my_list=match is not None, my_conference_id=match))
    return CatalogResponse(
        items=items,
        total=len(views),
        limit=limit,
        offset=offset,
        source=CatalogSource(
            name=conference_catalog.SOURCE_NAME,
            url=conference_catalog.SOURCE_URL,
            license=conference_catalog.SOURCE_LICENSE,
            data_url=snapshot.source_url,
        ),
        fetched_at=snapshot.fetched_at,
        stale=snapshot.stale,
        categories=[CatalogCategory(code=k, label=v) for k, v in sorted(conference_catalog.CATEGORIES.items())],
        topics=[
            CatalogTopic(id=t.id, label=t.label, in_prism_focus=t.id in conference_catalog.PRISM_FOCUS)
            for t in conference_catalog.TOPICS
        ],
    )


@router.post("/catalog/refresh", response_model=CatalogRefreshResponse)
def refresh_catalog(user: User = Depends(get_current_user)):
    snapshot = conference_catalog.get_catalog(force_refresh=True)
    return CatalogRefreshResponse(total=len(snapshot.conferences), fetched_at=snapshot.fetched_at, stale=snapshot.stale)


@router.post("/catalog/{key}/add", response_model=ConferenceResponse, status_code=status.HTTP_201_CREATED)
def add_catalog_conference(
    key: str,
    response: Response,
    data: CatalogAddRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conference = conference_catalog.get_catalog().by_key.get(key)
    if conference is None:
        raise NotFoundError("Conference not found in the catalog.")
    view = conference_catalog.catalog_view(conference, datetime.now(timezone.utc))
    record, existed = conference_service.add_from_catalog(db, user, view, data.project_id if data else None)
    result = _one(db, user, record)
    result.linked_existing = existed
    if existed:
        response.status_code = status.HTTP_200_OK
    return result


@router.get("/{conference_id}", response_model=ConferenceResponse)
def get_conference(conference_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _one(db, user, conference_service.get_conference(db, user, conference_id))


@router.patch("/{conference_id}", response_model=ConferenceResponse)
def update_conference(
    conference_id: UUID,
    data: ConferenceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _one(db, user, conference_service.update_conference(db, user, conference_id, data))


@router.delete("/{conference_id}", response_model=MessageResponse)
def delete_conference(conference_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conference_service.delete_conference(db, user, conference_id)
    return MessageResponse(message="Conference deleted.")


@router.post("/{conference_id}/projects", response_model=ConferenceResponse)
def link_conference(
    conference_id: UUID,
    data: ConferenceLinkRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _one(db, user, conference_service.link_conference(db, user, conference_id, data.project_id))


@router.post("/{conference_id}/projects/{project_id}/archive", response_model=MessageResponse)
def archive_link(
    conference_id: UUID, project_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    conference_service.archive_link(db, user, conference_id, project_id)
    return MessageResponse(message="Conference association archived.")


@router.delete("/{conference_id}/projects/{project_id}", response_model=MessageResponse)
def unlink_conference(
    conference_id: UUID, project_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    conference_service.unlink_conference(db, user, conference_id, project_id)
    return MessageResponse(message="Conference removed from the project.")
