"""Browse catalog of academic journals.

Two open sources are combined:

* **SCImago Journal Rank (SJR)**: the yearly journal list with SJR score,
  best quartile, h-index, subject areas and per-category quartiles. Free
  to use with attribution. When it is available it is the primary
  listing (browse/filter by lab domain and quartile, sort by SJR). It is
  downloaded once and cached on disk for 30 days. scimagojr.com sits
  behind a bot challenge that may block automated downloads, so a CSV
  saved by hand from the site to ``backend/data/scimagojr.csv`` is
  picked up as well.
* **OpenAlex Sources API** (CC0): live search over ~250k journals with
  publisher, homepage, open-access/DOAJ status, APC and citation
  metrics. Used to enrich SJR rows (one batched ISSN lookup per page) and
  as the listing itself whenever SJR data is unavailable.

Journals take submissions year round, so there is no deadline data;
special-issue calls are offered as search links instead of scraping.
"""

import csv
import io
import json
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import httpx

from app.core.config import settings
from app.core.errors import ServiceError

logger = logging.getLogger("prism.journal_catalog")

USER_AGENT = "PrismDesk/1.0"
DATA_DIR = Path(__file__).resolve().parents[2] / "data"

SJR_URL = "https://www.scimagojr.com/journalrank.php?out=xls"
SJR_NAME = "SCImago Journal & Country Rank (SJR)"
SJR_SITE = "https://www.scimagojr.com"
SJR_CACHE_FILE = DATA_DIR / "sjr_journals.json"
SJR_MANUAL_FILE = DATA_DIR / "scimagojr.csv"
SJR_TTL = timedelta(days=30)
SJR_FAILURE_BACKOFF = timedelta(hours=6)
SJR_TIMEOUT = httpx.Timeout(60.0, connect=8.0)
SJR_MAX_BYTES = 80_000_000
SJR_CACHE_VERSION = 1

OPENALEX_NAME = "OpenAlex"
OPENALEX_SITE = "https://openalex.org"
OPENALEX_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
OPENALEX_TTL = 3600.0
OPENALEX_MAX_PAGE_DEPTH = 10_000
OPENALEX_SELECT = ",".join(
    [
        "id",
        "display_name",
        "issn_l",
        "issn",
        "host_organization_name",
        "homepage_url",
        "works_count",
        "cited_by_count",
        "summary_stats",
        "is_oa",
        "is_in_doaj",
        "apc_usd",
        "topics",
    ]
)

QUARTILES = ("Q1", "Q2", "Q3", "Q4")


# PRISM Lab (Power-aware Resilient Intelligent Secure Machines) domains.
# The catalog only ever lists journals in these domains. Each domain maps
# to SJR (Scopus ASJC) category names and to OpenAlex subfield ids, which
# use the same ASJC codes.
@dataclass(frozen=True)
class Domain:
    id: str
    label: str
    sjr_categories: frozenset[str]
    subfields: frozenset[int]


CS_CATEGORIES = frozenset(
    {
        "Computer Science (miscellaneous)",
        "Artificial Intelligence",
        "Computational Theory and Mathematics",
        "Computer Graphics and Computer-Aided Design",
        "Computer Networks and Communications",
        "Computer Science Applications",
        "Computer Vision and Pattern Recognition",
        "Hardware and Architecture",
        "Human-Computer Interaction",
        "Information Systems",
        "Signal Processing",
        "Software",
    }
)
_ARCH = frozenset({"Hardware and Architecture"})
_ELECTRONICS = frozenset(
    {"Electrical and Electronic Engineering", "Control and Systems Engineering", "Signal Processing"}
)
_AI = frozenset({"Artificial Intelligence", "Computer Vision and Pattern Recognition"})

DOMAINS: tuple[Domain, ...] = (
    Domain("architecture", "Computer architecture & hardware", _ARCH, frozenset({1708})),
    Domain("electronics", "Electronics & electrical engineering", _ELECTRONICS, frozenset({2208, 2207, 1711})),
    Domain("ai", "AI & machine learning", _AI, frozenset({1702, 1707})),
    Domain(
        "cs_other",
        "Computer science (other)",
        CS_CATEGORIES - _ARCH - _ELECTRONICS - _AI,
        frozenset({1700, 1703, 1704, 1705, 1706, 1709, 1710, 1712}),
    ),
)
DOMAIN_BY_ID = {d.id: d for d in DOMAINS}
LAB_SUBFIELDS = frozenset().union(*(d.subfields for d in DOMAINS))
# A journal from OpenAlex counts as a lab journal when at least half of
# its works (by topic) fall in lab subfields; a domain is assigned when
# it holds at least this share of the journal's works.
OPENALEX_LAB_SHARE = 0.5
OPENALEX_DOMAIN_SHARE = 0.2
# Skip tiny/inactive venues in the OpenAlex listing.
OPENALEX_MIN_H_INDEX = 5
OPENALEX_SCAN_PAGES = 10
OPENALEX_SCAN_PAGE_SIZE = 100


def sjr_domains(journal: dict) -> list[str]:
    """Lab domains of an SJR journal; empty means outside the lab's scope."""
    names = {c["name"] for c in journal.get("categories") or []}
    domains = [d.id for d in DOMAINS if names & d.sjr_categories]
    if not domains and "Computer Science" in (journal.get("areas") or []):
        domains.append("cs_other")
    return domains


def openalex_domains(topics: list[dict]) -> tuple[list[str], float]:
    """(lab domains, lab share) from an OpenAlex source's topic counts."""
    counts: dict[str, float] = {}
    total = lab = 0.0
    for topic in topics or []:
        count = float((topic or {}).get("count") or 0)
        try:
            subfield = int(str(((topic or {}).get("subfield") or {}).get("id") or "").rsplit("/", 1)[-1])
        except ValueError:
            subfield = None
        total += count
        for domain in DOMAINS:
            if subfield in domain.subfields:
                counts[domain.id] = counts.get(domain.id, 0.0) + count
                lab += count
                break
    if not total:
        return [], 0.0
    share = lab / total
    domains = [d.id for d in DOMAINS if counts.get(d.id, 0) / total >= OPENALEX_DOMAIN_SHARE]
    if share >= OPENALEX_LAB_SHARE and not domains:
        domains = [max(counts, key=counts.get)]
    return domains, round(share, 3)

_ISSN = re.compile(r"^(\d{4})-?(\d{3}[\dX])$")
_CATEGORY = re.compile(r"^(.*?)\s*\((Q[1-4])\)\s*$")


class CatalogUnavailableError(ServiceError):
    status_code = 503


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def normalize_issn(value: Any) -> str | None:
    """``15424863`` / ``1542-4863`` / ``1542-486x`` → ``1542-4863``; else None."""
    text = re.sub(r"\s", "", str(value or "")).upper()
    match = _ISSN.match(text)
    return f"{match.group(1)}-{match.group(2)}" if match else None


def title_key(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower().replace("&", " and ")).strip()[:300]


def _float(value: Any) -> float | None:
    text = str(value or "").strip().replace(",", ".")
    try:
        return float(text) if text else None
    except ValueError:
        return None


def _int(value: Any) -> int | None:
    number = _float(value)
    return int(number) if number is not None else None


def _http_url(value: Any) -> str | None:
    text = str(value or "").strip()[:2048]
    return text if re.match(r"^https?://", text, re.IGNORECASE) else None


def special_issue_links(title: str) -> dict[str, str]:
    return {
        "wikicfp_url": f"http://www.wikicfp.com/cfp/servlet/tool.search?q={quote_plus(title)}&year=t",
        "google_special_issues_url": "https://www.google.com/search?q="
        + quote_plus(f'"{title}" special issue call for papers'),
    }


# ---------------------------------------------------------------------------
# SJR CSV
# ---------------------------------------------------------------------------


def parse_sjr_csv(text: str) -> list[dict]:
    """Parse SCImago's semicolon-separated export into journal dicts.

    Header names are matched case-insensitively so small format changes
    between yearly exports do not break parsing; non-journal rows
    (book series, conference proceedings) are skipped.
    """
    text = text.lstrip("﻿")
    reader = csv.reader(io.StringIO(text), delimiter=";", quotechar='"')
    try:
        header = [h.strip().lower() for h in next(reader)]
    except StopIteration:
        raise ValueError("The SJR file is empty.")

    def col(*names: str) -> int | None:
        for name in names:
            if name in header:
                return header.index(name)
        return None

    idx = {
        "rank": col("rank"),
        "sourceid": col("sourceid"),
        "title": col("title"),
        "type": col("type"),
        "issn": col("issn"),
        "sjr": col("sjr"),
        "quartile": col("sjr best quartile"),
        "h_index": col("h index"),
        "publisher": col("publisher"),
        "categories": col("categories"),
        "areas": col("areas"),
        "country": col("country"),
        "oa": col("open access"),
    }
    if idx["title"] is None or idx["issn"] is None:
        raise ValueError("The SJR file does not have the expected Title/Issn columns.")

    journals = []
    for row in reader:
        def get(key: str) -> str:
            i = idx[key]
            return row[i].strip() if i is not None and i < len(row) else ""

        if not row or not get("title"):
            continue
        kind = get("type").lower()
        if kind and kind != "journal":
            continue
        issns = [i for i in (normalize_issn(p) for p in re.split(r"[,\s]+", get("issn"))) if i]
        if not issns:
            continue
        categories = []
        for part in get("categories").split(";"):
            match = _CATEGORY.match(part.strip())
            if match:
                categories.append({"name": match.group(1), "quartile": match.group(2)})
            elif part.strip():
                categories.append({"name": part.strip(), "quartile": None})
        quartile = get("quartile").upper()
        journals.append(
            {
                "issn": issns[0],
                "issns": issns,
                "title": get("title")[:300],
                "publisher": get("publisher")[:300] or None,
                "sjr": _float(get("sjr")),
                "sjr_quartile": quartile if quartile in QUARTILES else None,
                "h_index": _int(get("h_index")),
                "sjr_rank": _int(get("rank")),
                "sourceid": get("sourceid") or None,
                "categories": categories[:30],
                "areas": [a.strip() for a in get("areas").split(";") if a.strip()][:15],
                "country": get("country")[:100] or None,
                "sjr_open_access": get("oa").lower() == "yes" if idx["oa"] is not None else None,
            }
        )
    if not journals:
        raise ValueError("No journals found in the SJR file.")
    return journals


@dataclass
class SjrSnapshot:
    journals: list[dict]
    fetched_at: datetime
    origin: str  # "download" or "manual"
    stale: bool = False
    by_issn: dict[str, dict] = field(default_factory=dict)

    def __post_init__(self):
        for journal in self.journals:
            journal["domains"] = sjr_domains(journal)
            for issn in journal["issns"]:
                self.by_issn.setdefault(issn, journal)


_sjr_lock = threading.Lock()
_sjr: SjrSnapshot | None = None
_sjr_loaded_from_disk = False
_sjr_failure_at: datetime | None = None
_sjr_error: str | None = None


def _download(url: str, timeout: httpx.Timeout, max_bytes: int) -> bytes:
    with httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            chunks, size = [], 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > max_bytes:
                    raise ValueError("Download is unexpectedly large.")
                chunks.append(chunk)
    return b"".join(chunks)


def _decode(content: bytes) -> str:
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _read_sjr_cache() -> SjrSnapshot | None:
    try:
        data = json.loads(SJR_CACHE_FILE.read_text(encoding="utf-8"))
        if data.get("version") != SJR_CACHE_VERSION:
            return None
        return SjrSnapshot(data["journals"], datetime.fromisoformat(data["fetched_at"]), data.get("origin", "download"))
    except FileNotFoundError:
        return None
    except Exception as error:  # noqa: BLE001 - a corrupt cache is ignored
        logger.warning("Ignoring unreadable SJR cache: %s", error)
        return None


def _write_sjr_cache(snapshot: SjrSnapshot) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        temp = SJR_CACHE_FILE.with_suffix(".tmp")
        temp.write_text(
            json.dumps(
                {
                    "version": SJR_CACHE_VERSION,
                    "fetched_at": snapshot.fetched_at.isoformat(),
                    "origin": snapshot.origin,
                    "journals": snapshot.journals,
                }
            ),
            encoding="utf-8",
        )
        temp.replace(SJR_CACHE_FILE)
    except OSError as error:
        logger.warning("Could not write SJR cache: %s", error)


def _manual_snapshot(current: SjrSnapshot | None) -> SjrSnapshot | None:
    """Use a hand-downloaded scimagojr.csv if it is newer than what we have."""
    try:
        mtime = datetime.fromtimestamp(SJR_MANUAL_FILE.stat().st_mtime, timezone.utc)
    except FileNotFoundError:
        return None
    if current is not None and current.fetched_at >= mtime:
        return None
    try:
        journals = parse_sjr_csv(_decode(SJR_MANUAL_FILE.read_bytes()))
    except Exception as error:  # noqa: BLE001
        logger.warning("Could not parse %s: %s", SJR_MANUAL_FILE, error)
        return None
    return SjrSnapshot(journals, mtime, "manual")


def get_sjr(force_refresh: bool = False) -> SjrSnapshot | None:
    """Return SJR data, or None when it has never been obtained.

    Never raises: SJR is optional and the catalog falls back to OpenAlex.
    """
    global _sjr, _sjr_loaded_from_disk, _sjr_failure_at, _sjr_error
    with _sjr_lock:
        now = datetime.now(timezone.utc)
        if not _sjr_loaded_from_disk:
            _sjr = _read_sjr_cache()
            _sjr_loaded_from_disk = True

        manual = _manual_snapshot(_sjr)
        if manual:
            _sjr = manual
            _write_sjr_cache(manual)

        fresh = _sjr is not None and now - _sjr.fetched_at < SJR_TTL
        if fresh and not force_refresh:
            return _sjr
        if not force_refresh and _sjr_failure_at and now - _sjr_failure_at < SJR_FAILURE_BACKOFF:
            if _sjr:
                _sjr.stale = True
            return _sjr

        try:
            journals = parse_sjr_csv(_decode(_download(SJR_URL, SJR_TIMEOUT, SJR_MAX_BYTES)))
        except Exception as error:  # noqa: BLE001 - keep serving what we have
            _sjr_failure_at = now
            _sjr_error = str(error)[:300]
            logger.warning("SJR download failed: %s", _sjr_error)
            if _sjr:
                _sjr.stale = not fresh
            return _sjr

        _sjr_failure_at = None
        _sjr_error = None
        _sjr = SjrSnapshot(journals, now, "download")
        _write_sjr_cache(_sjr)
        return _sjr


def sjr_status() -> dict:
    return {"last_error": _sjr_error, "manual_file": str(SJR_MANUAL_FILE)}


# ---------------------------------------------------------------------------
# OpenAlex
# ---------------------------------------------------------------------------

_oa_cache: dict[str, tuple[float, Any]] = {}
_oa_lock = threading.Lock()


def _openalex_get(path: str, params: dict) -> dict:
    params = dict(params)
    if settings.OPENALEX_API_KEY:
        params["api_key"] = settings.OPENALEX_API_KEY
    cache_key = path + "?" + "&".join(f"{k}={params[k]}" for k in sorted(params) if k != "api_key")
    with _oa_lock:
        hit = _oa_cache.get(cache_key)
        if hit and time.monotonic() - hit[0] < OPENALEX_TTL:
            return hit[1]
    try:
        with httpx.Client(timeout=OPENALEX_TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
            response = client.get(f"{settings.OPENALEX_API_URL.rstrip('/')}/{path}", params=params)
            response.raise_for_status()
            data = response.json()
    except Exception as error:  # noqa: BLE001
        logger.warning("OpenAlex request failed: %s", error)
        raise CatalogUnavailableError("The OpenAlex journal service could not be reached. Try again later.") from error
    with _oa_lock:
        if len(_oa_cache) > 500:
            _oa_cache.clear()
        _oa_cache[cache_key] = (time.monotonic(), data)
    return data


def normalize_openalex(source: dict) -> dict:
    stats = source.get("summary_stats") or {}
    issns = [i for i in (normalize_issn(x) for x in [source.get("issn_l"), *(source.get("issn") or [])]) if i]
    issns = list(dict.fromkeys(issns))
    domains, lab_share = openalex_domains(source.get("topics") or [])
    areas = []
    for topic in source.get("topics") or []:
        name = ((topic or {}).get("field") or {}).get("display_name")
        if name and name not in areas:
            areas.append(name)
    return {
        "issn": issns[0] if issns else None,
        "issns": issns,
        "title": str(source.get("display_name") or "").strip()[:300],
        "publisher": (source.get("host_organization_name") or None),
        "homepage_url": _http_url(source.get("homepage_url")),
        "openalex_id": str(source.get("id") or "").rsplit("/", 1)[-1] or None,
        "works_count": source.get("works_count"),
        "cited_by_count": source.get("cited_by_count"),
        "openalex_h_index": stats.get("h_index"),
        "two_year_mean_citedness": round(stats["2yr_mean_citedness"], 2)
        if isinstance(stats.get("2yr_mean_citedness"), (int, float))
        else None,
        "is_oa": bool(source.get("is_oa")),
        "is_in_doaj": bool(source.get("is_in_doaj")),
        "apc_usd": source.get("apc_usd"),
        "areas": areas[:10],
        "domains": domains,
        "lab_share": lab_share,
    }


def openalex_by_issn(issns: list[str]) -> dict[str, dict]:
    """Batch lookup (one request for up to 50 ISSNs). Keys are every ISSN."""
    wanted = list(dict.fromkeys(i for i in issns if i))[:50]
    if not wanted:
        return {}
    data = _openalex_get(
        "sources",
        {"filter": "issn:" + "|".join(wanted), "per-page": 50, "select": OPENALEX_SELECT},
    )
    result: dict[str, dict] = {}
    for source in data.get("results") or []:
        item = normalize_openalex(source)
        for issn in item["issns"]:
            result.setdefault(issn, item)
    return result


def openalex_lab_search(
    q: str | None, domain: str | None, sort: str, limit: int, offset: int
) -> tuple[list[dict], int, bool]:
    """Lab-domain journals from OpenAlex: (items, total, total_is_estimate).

    OpenAlex's ``topics.subfield.id`` filter matches a journal if *any*
    of its topics is in the subfield (so chemistry journals with a few
    electronics papers match), so results are narrowed with that filter
    and then kept only when lab topics dominate (``openalex_domains``).
    Raw pages are scanned until enough journals are found; if the scan
    stops early the total is extrapolated and flagged as an estimate.
    """
    wanted = DOMAIN_BY_ID.get(domain or "")
    subfields = wanted.subfields if wanted else LAB_SUBFIELDS
    filters = [
        "type:journal",
        "topics.subfield.id:" + "|".join(str(s) for s in sorted(subfields)),
        f"summary_stats.h_index:>{OPENALEX_MIN_H_INDEX - 1}",
    ]
    params: dict[str, Any] = {"select": OPENALEX_SELECT}
    if q and q.strip():
        issn = normalize_issn(q)
        if issn:
            filters.append(f"issn:{issn}")
        else:
            params["search"] = q.strip()[:200]
    params["filter"] = ",".join(filters)
    # "relevance" only means something with a text search; otherwise use h-index.
    if not (sort == "relevance" and "search" in params):
        params["sort"] = {
            "title": "display_name:asc",
            "citations": "cited_by_count:desc",
        }.get(sort, "summary_stats.h_index:desc")

    def keep(item: dict) -> bool:
        if not item["title"] or item["lab_share"] < OPENALEX_LAB_SHARE:
            return False
        return wanted is None or wanted.id in item["domains"]

    kept: list[dict] = []
    scanned = raw_total = 0
    exhausted = False
    for page in range(1, OPENALEX_SCAN_PAGES + 1):
        data = _openalex_get("sources", {**params, "per-page": OPENALEX_SCAN_PAGE_SIZE, "page": page})
        raw_total = int((data.get("meta") or {}).get("count") or 0)
        results = data.get("results") or []
        scanned += len(results)
        kept.extend(i for i in (normalize_openalex(r) for r in results) if keep(i))
        if len(results) < OPENALEX_SCAN_PAGE_SIZE or scanned >= raw_total:
            exhausted = True
            break
        if len(kept) > offset + limit:
            break

    if exhausted or not scanned:
        return kept[offset : offset + limit], len(kept), False
    estimate = max(len(kept), round(raw_total * len(kept) / scanned))
    return kept[offset : offset + limit], estimate, True


# ---------------------------------------------------------------------------
# Catalog items
# ---------------------------------------------------------------------------


def merge_item(sjr: dict | None, oa: dict | None) -> dict:
    """Combine an SJR row and/or an OpenAlex record into one catalog item."""
    base = sjr or oa or {}
    title = base.get("title") or ""
    issns = list(dict.fromkeys([*(sjr or {}).get("issns", []), *(oa or {}).get("issns", [])]))
    areas = (sjr or {}).get("areas") or (oa or {}).get("areas") or []
    sourceid = (sjr or {}).get("sourceid")
    item = {
        "issn": base.get("issn") or (issns[0] if issns else None),
        "issns": issns,
        "title": title,
        "publisher": (sjr or {}).get("publisher") or (oa or {}).get("publisher"),
        "homepage_url": (oa or {}).get("homepage_url"),
        "areas": areas,
        "domains": (sjr or {}).get("domains") if sjr else (oa or {}).get("domains", []),
        "categories": (sjr or {}).get("categories") or [],
        "sjr": (sjr or {}).get("sjr"),
        "sjr_quartile": (sjr or {}).get("sjr_quartile"),
        "sjr_rank": (sjr or {}).get("sjr_rank"),
        "h_index": (sjr or {}).get("h_index") or (oa or {}).get("openalex_h_index"),
        "country": (sjr or {}).get("country"),
        "two_year_mean_citedness": (oa or {}).get("two_year_mean_citedness"),
        "works_count": (oa or {}).get("works_count"),
        "cited_by_count": (oa or {}).get("cited_by_count"),
        "is_oa": (oa or {}).get("is_oa") if oa else bool((sjr or {}).get("sjr_open_access")),
        "is_in_doaj": (oa or {}).get("is_in_doaj", False),
        "apc_usd": (oa or {}).get("apc_usd"),
        "openalex_id": (oa or {}).get("openalex_id"),
        "openalex_url": f"https://openalex.org/{oa['openalex_id']}" if oa and oa.get("openalex_id") else None,
        "sjr_url": f"https://www.scimagojr.com/journalsearch.php?q={quote_plus(sourceid)}&tip=sid" if sourceid else None,
        "enriched": oa is not None,
        "submission_mode": "rolling",
        **special_issue_links(title),
    }
    return item


def filter_sjr(
    journals: list[dict],
    q: str | None = None,
    domain: str | None = None,
    quartile: str | None = None,
    sort: str = "sjr",
) -> list[dict]:
    """Filter SJR journals; only lab-domain journals are ever returned."""
    term = (q or "").strip().lower()
    issn = normalize_issn(q) if q else None
    wanted = domain if domain in DOMAIN_BY_ID else None
    quartile_u = (quartile or "").upper()
    result = []
    for journal in journals:
        domains = journal.get("domains")
        if domains is None:
            domains = journal["domains"] = sjr_domains(journal)
        if not domains or (wanted and wanted not in domains):
            continue
        if quartile_u and journal["sjr_quartile"] != quartile_u:
            continue
        if issn:
            if issn not in journal["issns"]:
                continue
        elif term and not (
            term in journal["title"].lower()
            or term in (journal["publisher"] or "").lower()
            or any(term in c["name"].lower() for c in journal["categories"])
        ):
            continue
        result.append(journal)

    if sort == "title":
        result.sort(key=lambda j: j["title"].lower())
    elif sort == "h_index":
        result.sort(key=lambda j: -(j["h_index"] or 0))
    elif sort == "relevance" and term and not issn:
        result.sort(key=lambda j: (not j["title"].lower().startswith(term), -(j["sjr"] or 0)))
    else:
        result.sort(key=lambda j: (j["sjr_rank"] is None, j["sjr_rank"] or 0, -(j["sjr"] or 0)))
    return result


@dataclass
class CatalogPage:
    items: list[dict]
    total: int
    mode: str  # "sjr" or "openalex"
    sjr: SjrSnapshot | None
    enrichment_error: str | None = None
    total_is_estimate: bool = False


def browse(
    q: str | None,
    domain: str | None,
    quartile: str | None,
    sort: str,
    limit: int,
    offset: int,
) -> CatalogPage:
    sjr = get_sjr()
    if sjr:
        rows = filter_sjr(sjr.journals, q, domain, quartile, sort)
        page = rows[offset : offset + limit]
        enrichment_error = None
        try:
            oa = openalex_by_issn([i for row in page for i in row["issns"][:2]])
        except CatalogUnavailableError as error:
            oa, enrichment_error = {}, error.detail
        items = []
        for row in page:
            match = next((oa[i] for i in row["issns"] if i in oa), None)
            items.append(merge_item(row, match))
        return CatalogPage(items, len(rows), "sjr", sjr, enrichment_error)

    # No SJR data: OpenAlex is the listing; quartile filtering is unavailable.
    results, total, estimated = openalex_lab_search(q, domain, sort, limit, offset)
    return CatalogPage([merge_item(None, r) for r in results], total, "openalex", None, None, estimated)


def lookup(issn: str) -> dict | None:
    """Full catalog item for one ISSN (SJR row + live OpenAlex enrichment)."""
    normalized = normalize_issn(issn)
    if not normalized:
        return None
    sjr = get_sjr()
    row = sjr.by_issn.get(normalized) if sjr else None
    try:
        oa_map = openalex_by_issn(row["issns"] if row else [normalized])
    except CatalogUnavailableError:
        if row is None:
            raise
        oa_map = {}
    oa = next((oa_map[i] for i in (row["issns"] if row else [normalized]) if i in oa_map), None)
    if row is None and oa is None:
        return None
    item = merge_item(row, oa)
    # Journals outside the lab's domains are not part of the catalog.
    return item if item["domains"] else None


def reset_cache() -> None:
    """Forget in-memory state (used by tests)."""
    global _sjr, _sjr_loaded_from_disk, _sjr_failure_at, _sjr_error
    with _sjr_lock:
        _sjr = None
        _sjr_loaded_from_disk = False
        _sjr_failure_at = None
        _sjr_error = None
    with _oa_lock:
        _oa_cache.clear()
