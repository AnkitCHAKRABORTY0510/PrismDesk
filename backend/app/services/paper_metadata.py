"""Resolve paper metadata from a DOI, arXiv ID, web link or title.

Used by the "Quick add" box on the paper form. Only metadata is fetched
(never paper files) and nothing is stored until the user saves the form.

Sources:
* DOI      -> Crossref (abstract falls back to OpenAlex; DataCite DOIs fall back to doi.org)
* arXiv    -> arXiv Atom API
* web link -> citation_* / dc.* / og: meta tags, enriched via Crossref when a DOI is found
* title    -> Crossref bibliographic search (best match)
"""

import logging
import re
from difflib import SequenceMatcher
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Literal
from urllib.parse import unquote

import httpx

from app.core.config import settings
from app.core.errors import NotFoundError, ServiceError
from app.schemas.research import normalize_doi
from app.services.doi_lookup import _clean, lookup_doi, parse_csl
from app.services.metadata_http import LookupUnavailableError, UnsafeUrlError, fetch

logger = logging.getLogger("prism.metadata")

Kind = Literal["doi", "arxiv", "url", "title"]

MIN_TITLE_LENGTH = 8
TITLE_CANDIDATES = 5
MIN_TITLE_SIMILARITY = 0.6

_ARXIV_NEW = r"\d{4}\.\d{4,5}(?:v\d+)?"
_ARXIV_OLD = r"[a-z]+(?:-[a-z]+)*(?:\.[a-z]{2})?/\d{7}(?:v\d+)?"
_ARXIV_ID = rf"(?:{_ARXIV_NEW}|{_ARXIV_OLD})"
_ARXIV_BARE = re.compile(rf"^(?:arxiv\s*:\s*)?({_ARXIV_ID})$", re.IGNORECASE)
_ARXIV_URL = re.compile(
    rf"^https?://(?:www\.|export\.)?arxiv\.org/(?:abs|pdf|html)/({_ARXIV_ID})(?:\.pdf)?/?(?:[?#].*)?$",
    re.IGNORECASE,
)
_ARXIV_DOI = re.compile(rf"^10\.48550/arxiv\.({_ARXIV_ID})$", re.IGNORECASE)
_DOI_LIKE = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi\s*:\s*)?10\.\d{4,9}/\S+$", re.IGNORECASE)
_VERSION = re.compile(r"v\d+$")
_YEAR = re.compile(r"\b(1[89]\d\d|2[01]\d\d)\b")

_ATOM = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


class LookupInputError(ServiceError):
    status_code = 422


@dataclass(frozen=True)
class Detected:
    kind: Kind
    value: str


def detect(query: str) -> Detected:
    """Work out what the user pasted."""

    text = query.strip().strip("<>").strip()
    if not text:
        raise LookupInputError("Paste a DOI, arXiv ID, link or paper title.")

    if match := _ARXIV_BARE.match(text) or _ARXIV_URL.match(text):
        return Detected("arxiv", match.group(1))

    unquoted = unquote(text)
    if _DOI_LIKE.match(unquoted):
        try:
            doi = normalize_doi(re.sub(r"^doi\s*:\s*", "doi:", unquoted, flags=re.IGNORECASE))
        except ValueError:
            doi = None
        if doi:
            doi = doi.rstrip(".,;")
            if match := _ARXIV_DOI.match(doi):
                return Detected("arxiv", match.group(1))
            return Detected("doi", doi)

    if re.match(r"^https?://", text, re.IGNORECASE):
        if re.search(r"\s", text):
            raise LookupInputError("This link contains spaces. Check it and try again.")
        return Detected("url", text)

    if re.match(r"^[a-z][a-z0-9+.-]*://", text, re.IGNORECASE):
        raise UnsafeUrlError("Only http:// and https:// links can be fetched.")

    if len(text) < MIN_TITLE_LENGTH:
        raise LookupInputError("That does not look like a DOI, arXiv ID or link. Paste a longer title to search.")
    return Detected("title", re.sub(r"\s+", " ", text)[:300])


def _result(**fields) -> dict:
    base = {
        "title": None,
        "authors": [],
        "abstract": "",
        "publication_year": None,
        "venue": None,
        "doi": None,
        "url": None,
        "keywords": [],
        "source": None,
        "matched_by": None,
    }
    base.update(fields)
    return base


# --- Crossref / OpenAlex -------------------------------------------------


def parse_crossref(message: dict) -> dict:
    doi = normalize_doi(message.get("DOI") or "") or ""
    data = parse_csl(message, doi)
    # JATS abstracts often start with an "Abstract" heading.
    data["abstract"] = re.sub(r"^abstract\s*[:.]?\s+", "", data["abstract"], flags=re.IGNORECASE)
    data["url"] = f"https://doi.org/{doi}" if doi else None
    data["source"] = "crossref"
    return data


def rebuild_abstract(inverted_index: dict | None) -> str:
    """OpenAlex stores abstracts as {word: [positions]}."""

    if not inverted_index:
        return ""
    positions: dict[int, str] = {}
    for word, indexes in inverted_index.items():
        for index in indexes or []:
            if isinstance(index, int):
                positions[index] = word
    return " ".join(positions[i] for i in sorted(positions))


def _openalex(doi: str) -> dict | None:
    """Best-effort extra details; failures are ignored."""

    try:
        response = fetch(
            f"{settings.OPENALEX_API_URL.rstrip('/')}/works/doi:{doi}",
            timeout=httpx.Timeout(5.0, connect=3.0),
            service="OpenAlex",
        )
        if not response.ok:
            return None
        data = response.json()
    except ServiceError:
        return None
    return data if isinstance(data, dict) else None


def _enrich_from_openalex(data: dict) -> dict:
    if data["abstract"] and data["keywords"]:
        return data
    work = _openalex(data["doi"])
    if not work:
        return data
    if not data["abstract"]:
        data["abstract"] = _clean(rebuild_abstract(work.get("abstract_inverted_index")))[:20000]
    if not data["keywords"]:
        data["keywords"] = [
            k["display_name"][:100] for k in work.get("keywords") or [] if isinstance(k, dict) and k.get("display_name")
        ][:20]
    return data


def lookup_crossref(doi: str) -> dict:
    response = fetch(
        f"{settings.CROSSREF_API_URL.rstrip('/')}/works/{doi}",
        accept="application/json",
        service="Crossref",
    )
    if response.status_code == 404:
        # Not a Crossref DOI (e.g. DataCite/Zenodo): try doi.org content negotiation.
        data = lookup_doi(doi)
        data["source"] = "doi.org"
    elif not response.ok:
        raise LookupUnavailableError(f"Crossref returned HTTP {response.status_code}.")
    else:
        body = response.json()
        message = body.get("message") if isinstance(body, dict) else None
        if not isinstance(message, dict):
            raise LookupUnavailableError("Crossref returned metadata in an unexpected format.")
        data = parse_crossref(message)
        data["doi"] = doi
    return _enrich_from_openalex(_result(**data))


def _title_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _clean(text).lower()).strip()


def title_similarity(query: str, candidate: str) -> float:
    return SequenceMatcher(None, _title_key(query), _title_key(candidate)).ratio()


def search_crossref_title(title: str) -> dict:
    """Crossref's relevance order is fuzzy, so pick the closest title among the top hits."""

    response = fetch(
        f"{settings.CROSSREF_API_URL.rstrip('/')}/works",
        params={"query.bibliographic": title, "rows": str(TITLE_CANDIDATES)},
        accept="application/json",
        service="Crossref",
    )
    if not response.ok:
        raise LookupUnavailableError(f"Crossref returned HTTP {response.status_code}.")
    body = response.json()
    items = ((body.get("message") or {}).get("items") or []) if isinstance(body, dict) else []
    scored = [
        (title_similarity(title, _clean(str((item.get("title") or [""])[0]))), index, item)
        for index, item in enumerate(items)
        if isinstance(item, dict) and item.get("DOI") and item.get("title")
    ]
    if not scored:
        raise NotFoundError("No paper matching this title was found. Try the DOI or a link instead.")
    # Highest similarity wins; Crossref's order breaks ties.
    similarity, _, best = max(scored, key=lambda row: (row[0], -row[1]))
    if similarity < MIN_TITLE_SIMILARITY:
        raise NotFoundError("No paper with a closely matching title was found. Try the DOI or a link instead.")
    return _enrich_from_openalex(_result(**parse_crossref(best)))


# --- arXiv ----------------------------------------------------------------


def parse_arxiv(xml_text: str, arxiv_id: str) -> dict:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        raise LookupUnavailableError("arXiv returned an unexpected response.")

    entry = root.find("a:entry", _ATOM)
    entry_id = (entry.findtext("a:id", "", _ATOM) if entry is not None else "") or ""
    title = _clean(entry.findtext("a:title", "", _ATOM)) if entry is not None else ""
    if entry is None or "api/errors" in entry_id or not title or title.lower() == "error":
        raise NotFoundError("No arXiv paper was found with this ID.")

    base_id = _VERSION.sub("", arxiv_id)
    journal_doi = entry.findtext("arxiv:doi", "", _ATOM).strip()
    try:
        doi = normalize_doi(journal_doi) if journal_doi else None
    except ValueError:
        doi = None
    published = entry.findtext("a:published", "", _ATOM)
    year_match = _YEAR.search(published or "")

    return _result(
        title=title[:500],
        authors=[
            _clean(author.findtext("a:name", "", _ATOM))[:200]
            for author in entry.findall("a:author", _ATOM)
            if _clean(author.findtext("a:name", "", _ATOM))
        ][:100],
        abstract=_clean(entry.findtext("a:summary", "", _ATOM))[:20000],
        publication_year=int(year_match.group(1)) if year_match else None,
        venue=_clean(entry.findtext("arxiv:journal_ref", "", _ATOM))[:300] or "arXiv",
        doi=doi or f"10.48550/arxiv.{base_id.lower()}",
        url=f"https://arxiv.org/abs/{base_id}",
        keywords=list(dict.fromkeys(c.get("term") for c in entry.findall("a:category", _ATOM) if c.get("term")))[:50],
        source="arxiv",
        arxiv_doi=f"10.48550/arxiv.{base_id.lower()}",
    )


def lookup_arxiv(arxiv_id: str) -> dict:
    response = fetch(
        settings.ARXIV_API_URL,
        params={"id_list": arxiv_id, "max_results": "1"},
        accept="application/atom+xml",
        service="arXiv",
    )
    if response.status_code in (400, 404):
        raise NotFoundError("No arXiv paper was found with this ID.")
    if not response.ok:
        raise LookupUnavailableError(f"arXiv returned HTTP {response.status_code}.")
    return parse_arxiv(response.text, arxiv_id)


# --- Web pages ------------------------------------------------------------


class _MetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, list[str]] = {}
        self.canonical: str | None = None
        self.page_title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attributes = {key.lower(): (value or "") for key, value in attrs}
        if tag == "meta":
            key = (attributes.get("name") or attributes.get("property") or "").strip().lower()
            content = attributes.get("content", "").strip()
            if key and content:
                self.meta.setdefault(key, []).append(content)
        elif tag == "link" and "canonical" in attributes.get("rel", "").lower().split():
            self.canonical = attributes.get("href") or None
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title and len(self.page_title) < 1000:
            self.page_title += data


def _split_keywords(values: list[str]) -> list[str]:
    keywords: list[str] = []
    for value in values:
        keywords.extend(part.strip() for part in re.split(r"[;,]", value) if part.strip())
    return [k[:100] for k in dict.fromkeys(keywords)][:50]


def parse_html_meta(html_text: str, page_url: str) -> dict:
    parser = _MetaParser()
    try:
        parser.feed(html_text)
        parser.close()
    except Exception:  # Malformed HTML: use whatever was collected.
        logger.info("HTML meta parsing stopped early")
    meta = parser.meta

    def first(*keys: str) -> str:
        for key in keys:
            for value in meta.get(key, []):
                if _clean(value):
                    return _clean(value)
        return ""

    def every(*keys: str) -> list[str]:
        for key in keys:
            values = [_clean(v) for v in meta.get(key, []) if _clean(v)]
            if values:
                return values
        return []

    doi = None
    keys = ("citation_doi", "dc.identifier", "dc.identifier.doi", "prism.doi", "bepress_citation_doi")
    for candidate in [_clean(v) for key in keys for v in meta.get(key, [])]:
        try:
            doi = normalize_doi(re.sub(r"^doi\s*:\s*", "doi:", candidate, flags=re.IGNORECASE))
        except ValueError:
            continue
        if doi:
            break

    authors = every("citation_author", "dc.creator", "author")
    if len(authors) == 1 and ";" in authors[0]:
        authors = [a.strip() for a in authors[0].split(";") if a.strip()]
    year = _YEAR.search(
        first("citation_publication_date", "citation_date", "citation_online_date", "citation_year", "dc.date",
              "dc.date.issued", "article:published_time")
    )
    arxiv_id = first("citation_arxiv_id")

    return _result(
        title=(first("citation_title", "dc.title", "og:title") or _clean(parser.page_title))[:500] or None,
        authors=[a[:200] for a in dict.fromkeys(authors)][:100],
        abstract=first("citation_abstract", "dc.description", "og:description", "description")[:20000],
        publication_year=int(year.group(1)) if year else None,
        venue=first("citation_journal_title", "citation_conference_title", "citation_inbook_title",
                    "citation_publisher", "dc.publisher")[:300] or None,
        doi=doi,
        url=page_url,
        keywords=_split_keywords(every("citation_keywords", "keywords", "dc.subject")),
        source="webpage",
        arxiv_id=arxiv_id if arxiv_id and _ARXIV_BARE.match(arxiv_id) else None,
    )


def _merge(primary: dict, fallback: dict) -> dict:
    """Prefer ``primary`` values; fill its empty fields from ``fallback``."""

    merged = dict(primary)
    for key, value in fallback.items():
        if not merged.get(key) and value:
            merged[key] = value
    return merged


def lookup_url(url: str) -> dict:
    response = fetch(url, accept="text/html,application/xhtml+xml;q=0.9,*/*;q=0.5", public_only=True,
                     service="the website")
    if response.status_code in (404, 410):
        raise NotFoundError("The page at this link was not found.")
    if response.status_code in (401, 403):
        raise NotFoundError("The website refused the request (it may need a login). Paste the DOI instead.")
    if not response.ok:
        raise LookupUnavailableError(f"The website returned HTTP {response.status_code}.")
    if response.content_type == "application/pdf" or response.content.startswith(b"%PDF"):
        raise LookupInputError("This link is a PDF file. Download it and use “Import from PDF”, or paste the DOI.")
    if response.content_type and "html" not in response.content_type and "xml" not in response.content_type:
        raise LookupInputError("This link is not a web page with paper details. Paste the DOI or arXiv ID instead.")

    page = parse_html_meta(response.text, url)
    enriched: dict | None = None
    try:
        if page["doi"]:
            enriched = lookup_crossref(page["doi"])
        elif page.get("arxiv_id"):
            enriched = lookup_arxiv(page["arxiv_id"])
    except ServiceError as error:
        logger.info("Could not enrich page metadata: %s", error.detail)

    if enriched:
        result = _merge(enriched, page)
        result["url"] = url
        result["source"] = f"webpage+{enriched['source']}"
        return result
    if not page["title"]:
        raise NotFoundError("No paper details were found on this page. Paste the DOI or arXiv ID instead.")
    return page


# --- Entry point ------------------------------------------------------------


def resolve(query: str) -> dict:
    """Return suggested metadata plus ``matched_by``/``source``.

    May include an internal ``arxiv_doi`` key used for duplicate checks.
    """

    detected = detect(query)
    if detected.kind == "doi":
        data = lookup_crossref(detected.value)
    elif detected.kind == "arxiv":
        data = lookup_arxiv(detected.value)
    elif detected.kind == "url":
        data = lookup_url(detected.value)
    else:
        data = search_crossref_title(detected.value)
    data["matched_by"] = detected.kind
    data.pop("arxiv_id", None)
    return data
