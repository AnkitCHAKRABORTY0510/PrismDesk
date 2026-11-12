from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, page_params
from app.core.errors import NotFoundError
from app.database.session import get_db
from app.models.user import User
from app.schemas.common import MessageResponse, Page, PageParams
from app.schemas.journal import (
    JournalCatalogAddRequest,
    JournalCatalogItem,
    JournalCatalogRefreshResponse,
    JournalCatalogResponse,
    JournalCatalogSource,
    JournalCreate,
    JournalDomain,
    JournalResponse,
    JournalUpdate,
)
from app.services import journal_catalog, journal_service

router = APIRouter(prefix="/journals", tags=["Journals"])

SJR_UNAVAILABLE_NOTE = (
    "SJR ranking data could not be downloaded automatically. Download the journal list "
    "from scimagojr.com/journalrank.php (\"Download data\") and save it as "
    "backend/data/scimagojr.csv to enable quartile filters."
)


def _one(db, journal) -> JournalResponse:
    return journal_service.journal_responses(db, [journal])[0]


@router.get("", response_model=Page[JournalResponse])
def list_journals(
    search: str | None = Query(default=None, max_length=200),
    deadline: Literal["special", "rolling"] | None = None,
    project_id: UUID | None = None,
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    journals, total = journal_service.list_journals(db, user, params, search, deadline, project_id)
    return Page(
        items=journal_service.journal_responses(db, journals),
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post("", response_model=JournalResponse, status_code=status.HTTP_201_CREATED)
def create_journal(data: JournalCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _one(db, journal_service.create_journal(db, user, data))


# --- Browse catalog (declared before "/{journal_id}") --------------------------


def _sources(page_sjr) -> tuple[JournalCatalogSource, JournalCatalogSource]:
    ranking = JournalCatalogSource(
        name=journal_catalog.SJR_NAME,
        url=journal_catalog.SJR_SITE,
        license="Free use with attribution",
        available=page_sjr is not None,
        fetched_at=page_sjr.fetched_at if page_sjr else None,
        stale=page_sjr.stale if page_sjr else False,
        note=None if page_sjr else SJR_UNAVAILABLE_NOTE,
    )
    metadata = JournalCatalogSource(
        name=journal_catalog.OPENALEX_NAME,
        url=journal_catalog.OPENALEX_SITE,
        license="CC0",
        available=True,
    )
    return ranking, metadata


@router.get("/catalog", response_model=JournalCatalogResponse)
def browse_catalog(
    q: str | None = Query(default=None, max_length=200),
    domain: Literal["lab", "architecture", "electronics", "ai", "cs_other"] = "lab",
    quartile: Literal["Q1", "Q2", "Q3", "Q4"] | None = None,
    sort: Literal["relevance", "sjr", "h_index", "title", "citations"] = "sjr",
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    page = journal_catalog.browse(q, None if domain == "lab" else domain, quartile, sort, limit, offset)
    matches = journal_service.catalog_matches(db, user, page.items)
    items = [
        JournalCatalogItem(**item, in_my_list=index in matches, my_journal_id=matches.get(index))
        for index, item in enumerate(page.items)
    ]
    ranking, metadata = _sources(page.sjr)
    if page.enrichment_error:
        metadata.available = False
        metadata.note = page.enrichment_error
    return JournalCatalogResponse(
        items=items,
        total=page.total,
        total_is_estimate=page.total_is_estimate,
        limit=limit,
        offset=offset,
        mode=page.mode,
        ranking_available=page.sjr is not None,
        ranking=ranking,
        metadata=metadata,
        domains=[JournalDomain(id=d.id, label=d.label) for d in journal_catalog.DOMAINS],
    )


@router.post("/catalog/refresh", response_model=JournalCatalogRefreshResponse)
def refresh_catalog(user: User = Depends(get_current_user)):
    snapshot = journal_catalog.get_sjr(force_refresh=True)
    return JournalCatalogRefreshResponse(
        ranking_available=snapshot is not None,
        total=len(snapshot.journals) if snapshot else 0,
        fetched_at=snapshot.fetched_at if snapshot else None,
        stale=snapshot.stale if snapshot else False,
        note=None if snapshot and not snapshot.stale else SJR_UNAVAILABLE_NOTE,
    )


@router.post("/catalog/{issn}/add", response_model=JournalResponse, status_code=status.HTTP_201_CREATED)
def add_catalog_journal(
    issn: str,
    response: Response,
    data: JournalCatalogAddRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    journal_service.require_create(user)
    item = journal_catalog.lookup(issn)
    if item is None:
        raise NotFoundError("Journal not found in the catalog.")
    journal, existed = journal_service.add_from_catalog(db, user, item, data.project_id if data else None)
    result = _one(db, journal)
    result.linked_existing = existed
    if existed:
        response.status_code = status.HTTP_200_OK
    return result


# --- Single journal ---------------------------------------------------------------


@router.get("/{journal_id}", response_model=JournalResponse)
def get_journal(journal_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _one(db, journal_service.get_journal(db, user, journal_id))


@router.patch("/{journal_id}", response_model=JournalResponse)
def update_journal(
    journal_id: UUID, data: JournalUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return _one(db, journal_service.update_journal(db, user, journal_id, data))


@router.delete("/{journal_id}", response_model=MessageResponse)
def delete_journal(journal_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    journal_service.delete_journal(db, user, journal_id)
    return MessageResponse(message="Journal removed from your list.")
