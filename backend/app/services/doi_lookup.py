"""Fetch paper metadata for a DOI using doi.org content negotiation.

doi.org resolves both Crossref and DataCite DOIs (including arXiv's
10.48550 DOIs) to CSL-JSON. Only metadata is fetched; never the paper.
"""

import html
import logging
import re

from app.core.config import settings
from app.core.errors import NotFoundError
from app.services.metadata_http import LookupUnavailableError, fetch

logger = logging.getLogger("prism.doi")

_TAGS = re.compile(r"<[^>]+>")

__all__ = ["LookupUnavailableError", "lookup_doi", "parse_csl"]


def _clean(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", html.unescape(_TAGS.sub(" ", text))).strip()


def _first(value) -> str | None:
    if isinstance(value, list):
        return value[0] if value else None
    return value


def parse_csl(data: dict, doi: str) -> dict:
    authors = []
    for author in data.get("author", []) or []:
        name = " ".join(part for part in (author.get("given"), author.get("family")) if part)
        name = name or author.get("literal") or author.get("name") or ""
        if name:
            authors.append(name.strip()[:200])

    year = None
    for key in ("published-print", "published-online", "issued", "published"):
        parts = (data.get(key) or {}).get("date-parts") or []
        if parts and parts[0] and parts[0][0]:
            year = int(parts[0][0])
            break

    keywords = data.get("subject") or []
    if isinstance(data.get("keyword"), str):
        keywords = keywords + [k.strip() for k in data["keyword"].split(",") if k.strip()]

    return {
        "title": _clean(_first(data.get("title")))[:500] or None,
        "authors": authors[:100],
        "abstract": _clean(data.get("abstract"))[:20000],
        "publication_year": year if year and 1800 <= year <= 2200 else None,
        "venue": _clean(_first(data.get("container-title")) or data.get("publisher"))[:300] or None,
        "doi": doi,
        "url": data.get("URL") or f"https://doi.org/{doi}",
        "keywords": [k[:100] for k in keywords][:50],
    }


def lookup_doi(doi: str) -> dict:
    response = fetch(
        f"{settings.DOI_LOOKUP_URL.rstrip('/')}/{doi}",
        accept="application/vnd.citationstyles.csl+json",
        service="doi.org",
    )
    if response.status_code == 404:
        raise NotFoundError("No metadata was found for this DOI.")
    if not response.ok:
        raise LookupUnavailableError(f"doi.org returned HTTP {response.status_code}.")

    data = response.json()
    if not isinstance(data, dict):
        raise LookupUnavailableError("doi.org returned metadata in an unexpected format.")
    return parse_csl(data, doi)
