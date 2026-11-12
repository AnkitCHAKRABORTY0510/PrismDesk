"""Browse-conference catalog (ccfddl/ccf-deadlines). No network: the
download is replaced with a small fixture YAML."""

import io
import tarfile
from datetime import datetime, timedelta, timezone

import pytest

from app.services import conference_catalog as catalog

C = "/api/v1/conferences"
NOW = datetime.now(timezone.utc)
NEXT = NOW.year + 1
PAST = NOW.year - 2


def _fixture_yaml() -> str:
    return f"""
- title: AAAI
  description: AAAI Conference on Artificial Intelligence
  sub: AI
  rank: {{ccf: A, core: A*, thcpl: A}}
  dblp: aaai
  conference_key: AI/aaai
  confs:
  - year: {PAST}
    id: aaai{PAST % 100}
    link: https://aaai.org/old/
    timeline:
    - deadline: '{PAST - 1}-08-15 23:59:59'
    timezone: UTC-12
    date: February 1-4, {PAST}
    place: Old City
  - year: {NEXT}
    id: aaai{NEXT % 100}
    link: https://aaai.org/conference/aaai/aaai-{NEXT % 100}/
    timeline:
    - abstract_deadline: '{NEXT}-08-01 23:59:59'
      deadline: '{NEXT}-08-08 23:59:59'
      comment: Main track
    - deadline: '{NEXT}-09-20 23:59:59'
      comment: Fast track
    timezone: AoE
    date: February 20-27, {NEXT + 1}
    place: Singapore
- title: VLDB
  description: International Conference on Very Large Data Bases
  sub: DB
  rank: {{ccf: A, core: A*, thcpl: A}}
  dblp: vldb
  conference_key: DB/vldb
  confs:
  - year: {NEXT}
    id: vldb{NEXT % 100}
    link: https://vldb.org/{NEXT}/
    timeline:
    - deadline: '{NEXT}-03-01 17:00:00'
    timezone: UTC+8
    date: August, {NEXT}
    place: Beijing, China
- title: ICSE
  description: International Conference on Software Engineering
  sub: SE
  rank: {{ccf: A, core: A*, thcpl: A}}
  dblp: icse
  conference_key: SE/icse
  confs:
  - year: {NEXT}
    id: icse{NEXT % 100}
    link: https://conf.researchr.org/home/icse-{NEXT}
    timeline:
    - deadline: TBD
    timezone: UTC-12
    date: TBD
    place: TBD
- title: OLDC
  description: A Discontinued Conference
  sub: CT
  rank: {{ccf: C, core: N, thcpl: N}}
  dblp: ''
  conference_key: CT/oldc
  confs:
  - year: {PAST}
    id: oldc{PAST % 100}
    link: not-a-url
    timeline:
    - deadline: '{PAST}-01-10 23:59:59'
    timezone: PT
    date: May, {PAST}
    place: Somewhere
"""


@pytest.fixture()
def fixture_catalog(monkeypatch, tmp_path):
    calls = {"count": 0, "fail": False}

    def fake_download(url):
        calls["count"] += 1
        if calls["fail"]:
            raise OSError("network down")
        return _fixture_yaml().encode()

    monkeypatch.setattr(catalog, "_download", fake_download)
    monkeypatch.setattr(catalog, "CACHE_FILE", tmp_path / "catalog.json")
    catalog.reset_cache()
    yield calls
    catalog.reset_cache()


# --- parsing ---------------------------------------------------------------


def test_timezone_conversion():
    assert catalog.parse_deadline("2027-05-01 23:59:59", catalog.parse_timezone("AoE")) == datetime(
        2027, 5, 2, 11, 59, 59, tzinfo=timezone.utc
    )
    assert catalog.parse_deadline("2027-05-01 23:59:59", catalog.parse_timezone("UTC-12")) == datetime(
        2027, 5, 2, 11, 59, 59, tzinfo=timezone.utc
    )
    assert catalog.parse_deadline("2027-05-01 08:00:00", catalog.parse_timezone("UTC+8")) == datetime(
        2027, 5, 1, 0, 0, 0, tzinfo=timezone.utc
    )
    assert catalog.parse_deadline("2027-05-01 12:00:00", catalog.parse_timezone("UTC")) == datetime(
        2027, 5, 1, 12, tzinfo=timezone.utc
    )
    assert catalog.parse_deadline("2027-05-01 12:00:00", catalog.parse_timezone("UTC+5:30")) == datetime(
        2027, 5, 1, 6, 30, tzinfo=timezone.utc
    )
    # PT follows daylight saving: PDT (UTC-7) in July, PST (UTC-8) in January.
    pt = catalog.parse_timezone("PT")
    assert catalog.parse_deadline("2027-07-01 12:00:00", pt).hour == 19
    assert catalog.parse_deadline("2027-01-01 12:00:00", pt).hour == 20
    # Unknown zones fall back to AoE.
    assert catalog.parse_timezone("Mars/Olympus") == catalog.parse_timezone("AoE")


def test_tbd_and_bad_deadlines_are_none():
    tz = catalog.parse_timezone("AoE")
    for value in ("TBD", "tba", "", None, "next spring"):
        assert catalog.parse_deadline(value, tz) is None
    # A bare date means the end of that day.
    assert catalog.parse_deadline("2027-05-01", timezone.utc) == datetime(2027, 5, 1, 23, 59, 59, tzinfo=timezone.utc)


def test_parse_and_view():
    conferences = {c["key"]: c for c in catalog.parse_catalog_yaml(_fixture_yaml())}
    assert set(conferences) == {"ai-aaai", "db-vldb", "se-icse", "ct-oldc"}

    aaai = catalog.catalog_view(conferences["ai-aaai"], NOW)
    assert aaai["deadline_status"] == "upcoming"
    assert aaai["year"] == NEXT and aaai["latest_year"] == NEXT
    assert aaai["next_deadline"] == datetime(NEXT, 8, 9, 11, 59, 59, tzinfo=timezone.utc).isoformat()
    assert aaai["next_abstract_deadline"] == datetime(NEXT, 8, 2, 11, 59, 59, tzinfo=timezone.utc).isoformat()
    assert aaai["next_deadline_comment"] == "Main track"
    assert aaai["core_rank"] == "A*" and aaai["ccf_rank"] == "A"
    assert aaai["place"] == "Singapore" and len(aaai["timeline"]) == 2
    assert aaai["wikicfp_url"] == "http://www.wikicfp.com/cfp/servlet/tool.search?q=AAAI&year=t"
    assert aaai["dblp_url"] == "https://dblp.org/db/conf/aaai/"

    icse = catalog.catalog_view(conferences["se-icse"], NOW)
    assert icse["deadline_status"] == "tbd" and icse["next_deadline"] is None
    assert icse["timeline"][0]["deadline_tbd"] is True

    old = catalog.catalog_view(conferences["ct-oldc"], NOW)
    assert old["deadline_status"] == "passed"
    assert old["core_rank"] is None  # "N" means unranked
    assert old["website_url"] is None  # non-http links are dropped
    assert old["dblp_url"] is None


def test_filter_and_sort():
    views = [catalog.catalog_view(c, NOW) for c in catalog.parse_catalog_yaml(_fixture_yaml())]
    keys = lambda items: [v["key"] for v in items]  # noqa: E731

    # Nearest dated deadline first, then TBD; passed ones hidden by default.
    assert keys(catalog.filter_and_sort(views)) == ["db-vldb", "ai-aaai", "se-icse"]
    assert keys(catalog.filter_and_sort(views, upcoming_only=False))[-1] == "ct-oldc"
    assert keys(catalog.filter_and_sort(views, upcoming_only=False, sort="name")) == [
        "ai-aaai", "se-icse", "ct-oldc", "db-vldb"
    ]
    assert keys(catalog.filter_and_sort(views, q="very large")) == ["db-vldb"]
    assert keys(catalog.filter_and_sort(views, q="singapore")) == ["ai-aaai"]
    assert keys(catalog.filter_and_sort(views, category="se")) == ["se-icse"]
    assert keys(catalog.filter_and_sort(views, core_rank="a*", category="AI")) == ["ai-aaai"]
    assert keys(catalog.filter_and_sort(views, ccf_rank="C")) == []
    assert keys(catalog.filter_and_sort(views, ccf_rank="C", upcoming_only=False)) == ["ct-oldc"]


def test_tarball_fallback():
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, body in {
            "ccf-deadlines-main/conference/AI/aaai.yml": _fixture_yaml().split("- title: VLDB")[0],
            "ccf-deadlines-main/conference/README.md": "ignored",
            "ccf-deadlines-main/other/x.yml": "- title: NOPE",
        }.items():
            data = body.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    items = catalog.parse_catalog_tarball(buffer.getvalue())
    assert [i["key"] for i in items] == ["ai-aaai"]


def test_fallback_and_stale_cache(fixture_catalog, monkeypatch):
    first = catalog.get_catalog()
    assert len(first.conferences) == 4 and not first.stale
    assert catalog.CACHE_FILE.exists()

    # A fresh process reads the disk cache without downloading.
    catalog.reset_cache()
    count = fixture_catalog["count"]
    assert len(catalog.get_catalog().conferences) == 4
    assert fixture_catalog["count"] == count

    # Expired cache + failing network: the old copy is served as stale.
    monkeypatch.setattr(catalog, "CACHE_TTL", timedelta(seconds=-1))
    fixture_catalog["fail"] = True
    stale = catalog.get_catalog()
    assert stale.stale and len(stale.conferences) == 4

    # Nothing cached at all and no network: 503-style error.
    catalog.reset_cache()
    catalog.CACHE_FILE.unlink()
    with pytest.raises(catalog.CatalogUnavailableError):
        catalog.get_catalog()


# --- API -------------------------------------------------------------------


def test_browse_endpoint(fixture_catalog, login, student, client):
    assert client.get(f"{C}/catalog").status_code == 401

    api = login(student)
    body = api.get(f"{C}/catalog").json()
    assert body["total"] == 3
    assert [i["acronym"] for i in body["items"]] == ["VLDB", "AAAI", "ICSE"]
    assert body["source"]["name"] == "ccfddl/ccf-deadlines" and body["source"]["license"] == "MIT"
    assert body["fetched_at"] and body["stale"] is False
    assert {"code": "AI", "label": "Artificial Intelligence"} in body["categories"]
    assert all(i["in_my_list"] is False for i in body["items"])

    page = api.get(f"{C}/catalog", params={"upcoming_only": "false", "sort": "name", "limit": 2, "offset": 2}).json()
    assert page["total"] == 4 and [i["acronym"] for i in page["items"]] == ["OLDC", "VLDB"]
    assert api.get(f"{C}/catalog", params={"core_rank": "A*", "q": "aaai"}).json()["total"] == 1

    assert api.post(f"{C}/catalog/refresh").status_code == 200


def test_add_from_catalog_and_dedup(fixture_catalog, login, student, make_project):
    api = login(student)
    project = make_project(student)

    created = api.post(f"{C}/catalog/ai-aaai/add")
    assert created.status_code == 201, created.text
    conf = created.json()
    assert conf["name"] == f"AAAI {NEXT}" and conf["acronym"] == "AAAI"
    assert conf["website_url"].startswith("https://aaai.org/conference/")
    assert conf["cfp_url"].startswith("http://www.wikicfp.com/")
    assert conf["location"] == "Singapore"
    assert datetime.fromisoformat(conf["submission_deadline"]) == datetime(NEXT, 8, 9, 11, 59, 59, tzinfo=timezone.utc)
    labels = [d["label"] for d in conf["important_dates"]]
    assert labels == ["Abstract deadline", "Submission deadline (Fast track)"]
    assert "CORE A*" in conf["notes"] and "ccfddl/ccf-deadlines" in conf["notes"]

    items = {i["key"]: i for i in api.get(f"{C}/catalog").json()["items"]}
    assert items["ai-aaai"]["in_my_list"] is True and items["ai-aaai"]["my_conference_id"] == conf["id"]
    assert items["db-vldb"]["in_my_list"] is False

    # Adding again reuses the record; with a project it is linked.
    again = api.post(f"{C}/catalog/ai-aaai/add", json={"project_id": str(project.id)})
    assert again.status_code == 200 and again.json()["id"] == conf["id"] and again.json()["linked_existing"] is True
    assert [p["project_id"] for p in again.json()["projects"]] == [str(project.id)]

    # A manually entered conference with the same edition name counts too.
    manual = api.post(C, json={"name": f"VLDB {NEXT}", "submission_deadline": (NOW + timedelta(days=9)).isoformat()})
    assert manual.status_code == 201
    vldb = api.post(f"{C}/catalog/db-vldb/add")
    assert vldb.status_code == 200 and vldb.json()["id"] == manual.json()["id"]

    assert api.post(f"{C}/catalog/se-icse/add").status_code == 400  # deadline TBD
    assert api.post(f"{C}/catalog/ct-oldc/add").status_code == 400  # passed
    assert api.post(f"{C}/catalog/nope/add").status_code == 404


def test_guest_cannot_add_from_catalog(fixture_catalog, login, guest):
    api = login(guest)
    assert api.get(f"{C}/catalog").status_code == 200
    assert api.post(f"{C}/catalog/ai-aaai/add").status_code == 403


# --- PRISM topic tags --------------------------------------------------------


def test_topic_tags():
    tags = catalog.topic_tags
    assert tags("ISCA", "International Symposium on Computer Architecture", "DS") == ["architecture", "systems"]
    assert "embedded" in tags("EMSOFT", "International Conference on Embedded Software", "MX")
    assert tags("CODES+ISSS", "Hardware/Software Co-design and System Synthesis", "DS") == ["embedded", "systems"]
    assert "vlsi" in tags("ASP-DAC", "Asia and South Pacific Design Automation Conference", "DS")
    assert "vlsi" in tags("ISCAS", "International Symposium on Circuits and Systems", "DS")
    assert "low_power" in tags("ISLPED", "Low Power Electronics and Design", "DS")
    assert "low_power" in tags("XYZ", "Workshop on Energy-Efficient Computing", "DS")
    # Keyword match on the full name, case-insensitive.
    assert "reliability" in tags("ATS", "IEEE Asian Test Symposium", "DS")
    assert "embedded" in tags("XYZ", "Symposium on CYBER-PHYSICAL Systems", "MX")
    # Software testing and SAT are not hardware test.
    assert "reliability" not in tags("ICST", "Conference on Software Testing", "SE")
    assert "reliability" not in tags("SAT", "Theory and Applications of Satisfiability Testing", "CT")
    assert tags("CHES", "Cryptographic Hardware and Embedded Systems", "SC") == ["embedded", "security"]
    assert tags("NeurIPS", "Neural Information Processing Systems", "AI") == ["ai"]
    assert tags("VLDB", "Very Large Data Bases", "DB") == []
    # Word boundaries: "Empowering" is not "power".
    assert "low_power" not in tags("XYZ", "Empowering Users", "HI")


def test_topic_filter_scope_and_search():
    conferences = catalog.parse_catalog_yaml(_fixture_yaml())
    views = [catalog.catalog_view(c, NOW) for c in conferences]
    # Add a tagged and an untagged interdisciplinary (MX) venue.
    views.append({**views[1], "key": "mx-rtss", "acronym": "RTSS", "name": "Real-Time Systems Symposium",
                  "category": "MX", "topics": ["embedded"]})
    views.append({**views[1], "key": "mx-ismb", "acronym": "ISMB", "name": "Intelligent Systems for Molecular Biology",
                  "category": "MX", "topics": []})
    keys = lambda items: [v["key"] for v in items]  # noqa: E731

    assert "mx-ismb" not in keys(catalog.filter_and_sort(views))
    assert "mx-ismb" in keys(catalog.filter_and_sort(views, scope="all"))
    assert keys(catalog.filter_and_sort(views, topic="embedded")) == ["mx-rtss"]
    assert set(keys(catalog.filter_and_sort(views, topic="prism"))) == {"mx-rtss", "ai-aaai"}
    assert keys(catalog.filter_and_sort(views, topic="systems")) == []
    # Topic labels are searchable.
    assert keys(catalog.filter_and_sort(views, q="real-time")) == ["mx-rtss"]
    assert keys(catalog.filter_and_sort(views, q="machine learning")) == ["ai-aaai"]


def test_topic_api(fixture_catalog, login, student):
    api = login(student)
    body = api.get(f"{C}/catalog", params={"topic": "prism"}).json()
    assert [i["acronym"] for i in body["items"]] == ["AAAI"]
    assert body["items"][0]["topics"] == ["ai"]
    topics = {t["id"]: t for t in body["topics"]}
    assert topics["architecture"]["in_prism_focus"] is True and topics["systems"]["in_prism_focus"] is False
    assert api.get(f"{C}/catalog", params={"topic": "gardening"}).status_code == 422
