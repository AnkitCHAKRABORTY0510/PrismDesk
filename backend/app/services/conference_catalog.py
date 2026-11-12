"""Browse catalog of computer science conferences.

The catalog comes from the community-maintained ccfddl/ccf-deadlines
project (MIT licence). Its bundled ``allconf.yml`` lists every tracked
conference with its CCF, CORE (ICORE) and THCPL ranks and the timeline
of each edition. We download it, normalise each entry once (deadlines
converted to UTC), and cache the result in memory (12 hours) and in a
JSON file on disk so the catalog survives restarts and keeps working
offline. When a refresh fails the last good copy is served as stale.

Whether a deadline is upcoming depends on the current time, so that is
computed per request in ``catalog_items`` and never cached.
"""

import io
import json
import logging
import re
import tarfile
import threading
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, quote_plus
from zoneinfo import ZoneInfo

import httpx
import yaml

from app.core.errors import ServiceError

logger = logging.getLogger("prism.conference_catalog")

SOURCE_NAME = "ccfddl/ccf-deadlines"
SOURCE_URL = "https://github.com/ccfddl/ccf-deadlines"
SOURCE_LICENSE = "MIT"
ALLCONF_URL = "https://ccfddl.github.io/conference/allconf.yml"
TARBALL_URL = "https://codeload.github.com/ccfddl/ccf-deadlines/tar.gz/refs/heads/main"

USER_AGENT = "PrismDesk/1.0"
TIMEOUT = httpx.Timeout(20.0, connect=6.0)
MAX_BYTES = 30_000_000
CACHE_TTL = timedelta(hours=12)
# Manual refreshes within this window reuse the copy just downloaded.
MIN_REFRESH_INTERVAL = timedelta(minutes=2)
# After a failed download, automatic refreshes wait this long before retrying.
FAILURE_BACKOFF = timedelta(minutes=10)
CACHE_FILE = Path(__file__).resolve().parents[2] / "data" / "conference_catalog.json"
CACHE_VERSION = 1

CATEGORIES = {
    "AI": "Artificial Intelligence",
    "CG": "Computer Graphics & Multimedia",
    "CT": "Theoretical Computer Science",
    "DB": "Databases, Data Mining & IR",
    "DS": "Computer Architecture & Systems",
    "HI": "Human-Computer Interaction",
    "MX": "Interdisciplinary & Emerging",
    "NW": "Computer Networks",
    "SC": "Network & Information Security",
    "SE": "Software Engineering & Languages",
}

# Topic tags for the PRISM Lab (Power-aware Resilient Intelligent Secure
# Machines). ccfddl's category codes are too coarse (DS lumps architecture,
# embedded systems and EDA together), so tags come from seed acronyms,
# keywords in the full name, and some whole categories. A venue can have
# several tags.
@dataclass(frozen=True)
class Topic:
    id: str
    label: str
    venues: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()  # regexes, matched case-insensitively on the full name
    categories: tuple[str, ...] = ()  # whole ccfddl categories
    keyword_skip_categories: tuple[str, ...] = ()


TOPICS: tuple[Topic, ...] = (
    Topic(
        "architecture",
        "Computer architecture",
        venues=("ISCA", "MICRO", "HPCA", "ASPLOS", "PACT", "ICS", "SC", "ICCD", "CF", "Hot Chips", "IISWC",
                "HiPEAC", "ASAP"),
        keywords=(r"computer architecture", r"microarchitecture", r"architectural support",
                  r"parallel architectures", r"high[- ]performance chips", r"computer design"),
    ),
    Topic(
        "embedded",
        "Embedded & real-time systems",
        venues=("EMSOFT", "CODES+ISSS", "CASES", "LCTES", "RTAS", "RTSS", "ECRTS", "ESWEEK"),
        keywords=(r"\bembedded", r"real[- ]time", r"cyber[- ]physical"),
    ),
    Topic(
        "vlsi",
        "VLSI, EDA & FPGA",
        venues=("DAC", "ICCAD", "DATE", "ASP-DAC", "ISPD", "GLSVLSI", "ISLPED", "FPGA", "FCCM", "FPL", "FPT",
                "ISCAS"),
        keywords=(r"design automation", r"computer[- ]aided design", r"\bcircuit", r"\bfpga",
                  r"field[- ]programmable", r"\bvlsi", r"physical design"),
    ),
    Topic(
        "low_power",
        "Low-power & energy-efficient",
        venues=("ISLPED",),
        keywords=(r"\bpower\b", r"low[- ]power", r"\benergy"),
    ),
    Topic(
        "reliability",
        "Reliability & test",
        venues=("DSN", "ITC", "ITC-Asia", "ATS", "VTS", "ETS", "IOLTS", "DFT"),
        keywords=(r"dependab", r"\bfault", r"reliab", r"\btest(?:ing)?\b"),
        # Software-testing and satisfiability ("SAT testing") venues are not hardware test.
        keyword_skip_categories=("SE", "CT"),
    ),
    Topic(
        "security",
        "Hardware & systems security",
        venues=("HOST", "CHES", "CCS", "USENIX Security", "S&P", "NDSS"),
        keywords=(r"security", r"cryptograph"),
        categories=("SC",),
    ),
    Topic(
        "ai",
        "AI & machine learning",
        venues=("NeurIPS", "ICML", "ICLR", "AAAI", "IJCAI", "CVPR", "ICCV", "ECCV", "ACL", "EMNLP", "KDD",
                "SIGKDD", "MLSys"),
        keywords=(r"machine learning", r"artificial intelligence", r"neural", r"learning representations"),
        categories=("AI",),
    ),
    Topic(
        "systems",
        "Systems & networking",
        venues=("OSDI", "SOSP", "EuroSys", "ATC", "SIGOPS ATC", "USENIX ATC", "NSDI", "SIGCOMM"),
        categories=("NW", "DS"),
    ),
)
TOPIC_LABELS = {t.id: t.label for t in TOPICS}
# The "PRISM focus" preset.
PRISM_FOCUS = ("architecture", "embedded", "vlsi", "low_power", "reliability", "security", "ai")
# Every ccfddl category is computer science, so all are kept, but the
# "interdisciplinary" bucket (MX: bioinformatics, education, web, ...) is
# only kept for venues that match a lab topic (EMSOFT, RTSS, MLSys...).
LAB_CATEGORIES_TAGGED_ONLY = ("MX",)


def _venue_key(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


_TOPIC_VENUES = {t.id: {_venue_key(v) for v in t.venues} for t in TOPICS}
_TOPIC_PATTERNS = {t.id: [re.compile(k, re.IGNORECASE) for k in t.keywords] for t in TOPICS}


def topic_tags(acronym: str, name: str, category: str | None) -> list[str]:
    key = _venue_key(acronym)
    tags = []
    for topic in TOPICS:
        if key in _TOPIC_VENUES[topic.id] or (category and category in topic.categories):
            tags.append(topic.id)
        elif category not in topic.keyword_skip_categories and any(
            p.search(name) for p in _TOPIC_PATTERNS[topic.id]
        ):
            tags.append(topic.id)
    return tags


# Named zones seen (or likely) in the data. DST-aware where relevant.
NAMED_ZONES = {
    "AOE": timezone(timedelta(hours=-12)),
    "UTC": timezone.utc,
    "GMT": timezone.utc,
    "Z": timezone.utc,
    "PT": ZoneInfo("America/Los_Angeles"),
    "PST": timezone(timedelta(hours=-8)),
    "PDT": timezone(timedelta(hours=-7)),
    "MT": ZoneInfo("America/Denver"),
    "CT": ZoneInfo("America/Chicago"),
    "ET": ZoneInfo("America/New_York"),
    "EST": timezone(timedelta(hours=-5)),
    "EDT": timezone(timedelta(hours=-4)),
    "CET": ZoneInfo("Europe/Paris"),
    "CEST": timezone(timedelta(hours=2)),
    "BST": timezone(timedelta(hours=1)),
    "JST": timezone(timedelta(hours=9)),
    "KST": timezone(timedelta(hours=9)),
}
DEFAULT_ZONE_NAME = "AoE"
_OFFSET = re.compile(r"^(?:UTC|GMT)\s*([+-])\s*(\d{1,2})(?::?(\d{2}))?$", re.IGNORECASE)
_DEADLINE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d")


class CatalogUnavailableError(ServiceError):
    status_code = 503


# ---------------------------------------------------------------------------
# Parsing and normalisation (pure functions, covered by unit tests)
# ---------------------------------------------------------------------------


def parse_timezone(value: Any):
    """Return a tzinfo for ccfddl's timezone strings (AoE, UTC-12, UTC+8, PT…).

    Unknown or missing values fall back to AoE (UTC-12), ccfddl's most
    common convention.
    """
    text = str(value or "").strip()
    if not text:
        return NAMED_ZONES["AOE"]
    named = NAMED_ZONES.get(text.upper())
    if named:
        return named
    match = _OFFSET.match(text)
    if match:
        sign, hours, minutes = match.groups()
        offset = timedelta(hours=int(hours), minutes=int(minutes or 0))
        if offset <= timedelta(hours=14):
            return timezone(-offset if sign == "-" else offset)
    logger.debug("Unknown conference timezone %r, assuming AoE", text)
    return NAMED_ZONES["AOE"]


def parse_deadline(value: Any, tz) -> datetime | None:
    """Convert a local deadline to an aware UTC datetime. ``TBD``/blank → None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        local = value
    elif isinstance(value, date):
        local = datetime(value.year, value.month, value.day, 23, 59, 59)
    else:
        text = str(value).strip()
        if not text or text.upper() in {"TBD", "TBA", "N/A", "NONE"}:
            return None
        local = None
        for fmt in _DEADLINE_FORMATS:
            try:
                local = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        if local is None:
            return None
        if len(text) == 10:
            local = local.replace(hour=23, minute=59, second=59)
    if local.tzinfo is None:
        local = local.replace(tzinfo=tz)
    return local.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _text(value: Any, limit: int) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text[:limit] or None


def _http_url(value: Any) -> str | None:
    text = _text(value, 2048)
    return text if text and re.match(r"^https?://", text, re.IGNORECASE) else None


def _rank(value: Any) -> str | None:
    text = _text(value, 10)
    return None if text is None or text.upper() in {"N", "NONE", "-"} else text


def _key(entry: dict, fallback_sub: str | None = None) -> str:
    raw = entry.get("conference_key") or f"{entry.get('sub') or fallback_sub or 'XX'}/{entry.get('title') or ''}"
    return re.sub(r"[^a-z0-9]+", "-", str(raw).lower()).strip("-")


def normalize_entry(entry: dict, fallback_sub: str | None = None) -> dict | None:
    """Turn one ccfddl conference into a cache-friendly dict (UTC ISO strings)."""
    title = _text(entry.get("title"), 50)
    if not isinstance(entry, dict) or not title:
        return None
    rank = entry.get("rank") if isinstance(entry.get("rank"), dict) else {}
    dblp = _text(entry.get("dblp"), 100)

    editions = []
    for conf in entry.get("confs") or []:
        if not isinstance(conf, dict):
            continue
        try:
            year = int(conf.get("year"))
        except (TypeError, ValueError):
            continue
        zone_name = _text(conf.get("timezone"), 20) or DEFAULT_ZONE_NAME
        tz = parse_timezone(zone_name)
        timeline = []
        for item in conf.get("timeline") or []:
            if not isinstance(item, dict):
                continue
            deadline = parse_deadline(item.get("deadline"), tz)
            timeline.append(
                {
                    "deadline": _iso(deadline),
                    "abstract_deadline": _iso(parse_deadline(item.get("abstract_deadline"), tz)),
                    "comment": _text(item.get("comment"), 200),
                    "deadline_tbd": deadline is None,
                }
            )
        editions.append(
            {
                "year": year,
                "id": _text(conf.get("id"), 50),
                "link": _http_url(conf.get("link")),
                "timezone": zone_name,
                "date": _text(conf.get("date"), 100),
                "place": _text(conf.get("place"), 200),
                "timeline": timeline,
            }
        )
    editions.sort(key=lambda e: e["year"])

    sub = _text(entry.get("sub"), 10) or fallback_sub
    return {
        "key": _key(entry, fallback_sub),
        "acronym": title,
        "name": _text(entry.get("description"), 300) or title,
        "category": sub,
        "ccf_rank": _rank(rank.get("ccf")),
        "core_rank": _rank(rank.get("core")),
        "thcpl_rank": _rank(rank.get("thcpl")),
        "dblp": dblp,
        "editions": editions,
    }


def parse_catalog_yaml(text: str | bytes) -> list[dict]:
    data = yaml.safe_load(text)
    if not isinstance(data, list):
        raise ValueError("Unexpected catalog format: expected a list of conferences.")
    items = [normalize_entry(entry) for entry in data if isinstance(entry, dict)]
    return _dedupe_keys([item for item in items if item])


def parse_catalog_tarball(content: bytes) -> list[dict]:
    """Read ``conference/<SUB>/<name>.yml`` files out of the repo tarball."""
    items: list[dict] = []
    with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as archive:
        for member in archive:
            parts = member.name.split("/")
            # <repo-root>/conference/<SUB>/<name>.yml
            if not member.isfile() or len(parts) != 4 or parts[1] != "conference":
                continue
            if not parts[3].endswith((".yml", ".yaml")) or member.size > 2_000_000:
                continue
            handle = archive.extractfile(member)
            if handle is None:
                continue
            try:
                data = yaml.safe_load(handle.read())
            except yaml.YAMLError:
                logger.warning("Skipping unparsable catalog file %s", member.name)
                continue
            sub = parts[2]
            stem = parts[3].rsplit(".", 1)[0]
            for entry in data if isinstance(data, list) else []:
                if isinstance(entry, dict):
                    entry.setdefault("conference_key", f"{sub}/{stem}")
                    item = normalize_entry(entry, sub)
                    if item:
                        items.append(item)
    if not items:
        raise ValueError("No conference files found in the archive.")
    return _dedupe_keys(items)


def _dedupe_keys(items: list[dict]) -> list[dict]:
    seen: dict[str, int] = {}
    for item in items:
        count = seen.get(item["key"], 0)
        seen[item["key"]] = count + 1
        if count:
            item["key"] = f"{item['key']}-{count + 1}"
    return items


# ---------------------------------------------------------------------------
# Per-request view (depends on "now")
# ---------------------------------------------------------------------------


def wikicfp_url(acronym: str) -> str:
    return f"http://www.wikicfp.com/cfp/servlet/tool.search?q={quote_plus(acronym)}&year=t"


def dblp_url(dblp: str | None) -> str | None:
    return f"https://dblp.org/db/conf/{quote(dblp, safe='/')}/" if dblp else None


def _dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def catalog_view(conf: dict, now: datetime) -> dict:
    """Pick the edition to show and the next deadline for one conference.

    ``deadline_status`` is ``upcoming`` (a dated deadline in the future),
    ``tbd`` (a current/future edition whose deadline is not announced) or
    ``passed``.
    """
    editions = conf["editions"]
    best = None  # (deadline, edition, timeline item)
    for edition in editions:
        for item in edition["timeline"]:
            deadline = _dt(item["deadline"])
            if deadline and deadline >= now and (best is None or deadline < best[0]):
                best = (deadline, edition, item)

    if best:
        status, (_, edition, item) = "upcoming", best
    else:
        item = None
        tbd = [
            e for e in editions
            if e["year"] >= now.year and (not e["timeline"] or any(t["deadline_tbd"] for t in e["timeline"]))
        ]
        edition = tbd[-1] if tbd else (editions[-1] if editions else None)
        status = "tbd" if tbd else "passed"

    if edition is None:
        edition = {"year": None, "link": None, "timezone": None, "date": None, "place": None, "timeline": []}

    return {
        "key": conf["key"],
        "acronym": conf["acronym"],
        "name": conf["name"],
        "category": conf["category"],
        "category_label": CATEGORIES.get(conf["category"] or "", conf["category"]),
        "ccf_rank": conf["ccf_rank"],
        "core_rank": conf["core_rank"],
        "year": edition["year"],
        "latest_year": editions[-1]["year"] if editions else None,
        "website_url": edition["link"],
        "conference_dates": edition["date"],
        "place": edition["place"],
        "timezone": edition["timezone"],
        "deadline_status": status,
        "next_deadline": item["deadline"] if item else None,
        "next_abstract_deadline": item["abstract_deadline"] if item else None,
        "next_deadline_comment": item["comment"] if item else None,
        "timeline": edition["timeline"],
        "wikicfp_url": wikicfp_url(conf["acronym"]),
        "dblp_url": dblp_url(conf["dblp"]),
        "topics": topic_tags(conf["acronym"], conf["name"], conf["category"]),
    }


def filter_and_sort(
    views: list[dict],
    q: str | None = None,
    category: str | None = None,
    core_rank: str | None = None,
    ccf_rank: str | None = None,
    upcoming_only: bool = True,
    sort: str = "deadline",
    topic: str | None = None,
    scope: str = "lab",
) -> list[dict]:
    term = (q or "").strip().lower()
    wanted_topics = set(PRISM_FOCUS) if topic == "prism" else ({topic} if topic else None)
    result = []
    for view in views:
        if scope == "lab" and view["category"] in LAB_CATEGORIES_TAGGED_ONLY and not view["topics"]:
            continue
        if wanted_topics is not None and not wanted_topics.intersection(view["topics"]):
            continue
        if upcoming_only and view["deadline_status"] == "passed":
            continue
        if category and (view["category"] or "").upper() != category.upper():
            continue
        if core_rank and (view["core_rank"] or "").upper() != core_rank.upper():
            continue
        if ccf_rank and (view["ccf_rank"] or "").upper() != ccf_rank.upper():
            continue
        if term and not (
            any(term in (view[field] or "").lower() for field in ("acronym", "name", "place"))
            or any(term in TOPIC_LABELS[t].lower() for t in view["topics"])
        ):
            continue
        result.append(view)

    if sort == "name":
        result.sort(key=lambda v: (v["acronym"].lower(), v["key"]))
    else:
        status_order = {"upcoming": 0, "tbd": 1, "passed": 2}
        result.sort(
            key=lambda v: (
                status_order[v["deadline_status"]],
                v["next_deadline"] or "",
                v["acronym"].lower(),
            )
        )
    return result


# ---------------------------------------------------------------------------
# Download and cache
# ---------------------------------------------------------------------------


@dataclass
class CatalogSnapshot:
    conferences: list[dict]
    fetched_at: datetime
    source_url: str
    stale: bool = False

    @property
    def by_key(self) -> dict[str, dict]:
        return {c["key"]: c for c in self.conferences}


_lock = threading.Lock()
_memory: CatalogSnapshot | None = None
_last_error: str | None = None
_last_failure_at: datetime | None = None


def _download(url: str) -> bytes:
    with httpx.Client(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            chunks, size = [], 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError("Catalog download is unexpectedly large.")
                chunks.append(chunk)
    return b"".join(chunks)


def fetch_remote() -> CatalogSnapshot:
    """Download and parse the catalog, falling back to the repo tarball."""
    now = datetime.now(timezone.utc)
    try:
        return CatalogSnapshot(parse_catalog_yaml(_download(ALLCONF_URL)), now, ALLCONF_URL)
    except Exception as error:  # noqa: BLE001 - any failure triggers the fallback
        logger.warning("allconf.yml unavailable (%s); trying repository tarball", error)
    return CatalogSnapshot(parse_catalog_tarball(_download(TARBALL_URL)), now, TARBALL_URL)


def _read_disk() -> CatalogSnapshot | None:
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        if data.get("version") != CACHE_VERSION:
            return None
        return CatalogSnapshot(
            conferences=data["conferences"],
            fetched_at=datetime.fromisoformat(data["fetched_at"]),
            source_url=data.get("source_url", ALLCONF_URL),
        )
    except FileNotFoundError:
        return None
    except Exception as error:  # noqa: BLE001 - a corrupt cache is just ignored
        logger.warning("Ignoring unreadable catalog cache %s: %s", CACHE_FILE, error)
        return None


def _write_disk(snapshot: CatalogSnapshot) -> None:
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        temp = CACHE_FILE.with_suffix(".tmp")
        temp.write_text(
            json.dumps(
                {
                    "version": CACHE_VERSION,
                    "fetched_at": snapshot.fetched_at.isoformat(),
                    "source_url": snapshot.source_url,
                    "conferences": snapshot.conferences,
                }
            ),
            encoding="utf-8",
        )
        temp.replace(CACHE_FILE)
    except OSError as error:
        logger.warning("Could not write catalog cache %s: %s", CACHE_FILE, error)


def _fresh(snapshot: CatalogSnapshot | None, now: datetime, ttl: timedelta | None = None) -> bool:
    return snapshot is not None and now - snapshot.fetched_at < (CACHE_TTL if ttl is None else ttl)


def get_catalog(force_refresh: bool = False) -> CatalogSnapshot:
    """Return the catalog, downloading it when the cache is missing or old.

    If downloading fails, the last good copy (memory or disk) is returned
    with ``stale=True``; only when there is no copy at all is
    ``CatalogUnavailableError`` raised.
    """
    global _memory, _last_error, _last_failure_at
    with _lock:
        now = datetime.now(timezone.utc)
        if _memory is None:
            _memory = _read_disk()

        if force_refresh:
            if _fresh(_memory, now, MIN_REFRESH_INTERVAL) and not _memory.stale:
                return _memory
        elif _fresh(_memory, now):
            return _memory
        elif _memory is not None and _last_failure_at and now - _last_failure_at < FAILURE_BACKOFF:
            # Offline: keep serving the old copy without waiting on timeouts.
            _memory.stale = True
            return _memory

        try:
            snapshot = fetch_remote()
        except Exception as error:  # noqa: BLE001 - serve stale data instead
            _last_error = str(error)
            _last_failure_at = now
            logger.warning("Conference catalog refresh failed: %s", error)
            if _memory is None:
                raise CatalogUnavailableError(
                    "The conference catalog could not be downloaded. Try again later."
                ) from error
            _memory.stale = True
            return _memory

        _last_error = None
        _last_failure_at = None
        _memory = snapshot
        _write_disk(snapshot)
        return snapshot


def reset_cache() -> None:
    """Forget the in-memory copy (used by tests)."""
    global _memory, _last_error, _last_failure_at
    with _lock:
        _memory = None
        _last_error = None
        _last_failure_at = None
