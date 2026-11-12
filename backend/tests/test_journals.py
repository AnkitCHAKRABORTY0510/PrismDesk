"""Journal list and journal catalog (SJR + OpenAlex). No network: the SJR
download and OpenAlex API are replaced with fixtures."""

from datetime import datetime, timedelta, timezone

import pytest

from app.services import journal_catalog as catalog

J = "/api/v1/journals"

SJR_CSV = (
    "﻿Rank;Sourceid;Title;Type;Issn;Publisher;Open Access;SJR;SJR Best Quartile;H index;"
    "Total Docs. (2024);Country;Region;Coverage;Categories;Areas\n"
    '1;21100;"IEEE Transactions on Pattern Analysis and Machine Intelligence";journal;"19393539, 01628828";'
    '"IEEE Computer Society";No;"20,123";Q1;512;300;United States;Northern America;1979-2025;'
    '"Artificial Intelligence (Q1); Computer Vision and Pattern Recognition (Q1); Software (Q1)";"Computer Science; Mathematics"\n'
    '2;12345;"Journal of Machine Learning Research";journal;"15324435, 15337928";"Microtome Publishing";Yes;'
    '"5,5";Q1;250;200;United States;Northern America;2000-2025;'
    '"Artificial Intelligence (Q1); Software (Q1)";"Computer Science"\n'
    '3;99999;"Some Proceedings";conference and proceedings;"12345678";"ACM";No;"1,0";Q2;10;10;US;NA;2020;'
    '"Software (Q2)";"Computer Science"\n'
    '4;55555;"Regional Computing Letters";journal;"2049-136X";"Small Press";No;"0,2";Q4;5;20;India;Asiatic Region;'
    '2015-2025;"Computer Science Applications (Q4)";"Computer Science"\n'
    '5;77777;"Annals of Algebra";journal;"00034444";"Math Society";No;"3,1";Q1;80;50;Germany;Western Europe;'
    '1950-2025;"Algebra and Number Theory (Q1)";"Mathematics"\n'
    '6;66666;"IEEE Journal of Solid-State Circuits";journal;"00189200";"IEEE";No;"4,2";Q1;300;100;United States;'
    'Northern America;1966-2025;"Electrical and Electronic Engineering (Q1)";"Engineering"\n'
    '7;88888;"IEEE Micro";journal;"02721732";"IEEE";No;"1,1";Q2;120;60;United States;Northern America;'
    '1981-2025;"Hardware and Architecture (Q2); Software (Q2)";"Computer Science"\n'
)

OPENALEX = {
    "0162-8828": {
        "id": "https://openalex.org/S199944782",
        "display_name": "IEEE Transactions on Pattern Analysis and Machine Intelligence",
        "issn_l": "0162-8828",
        "issn": ["0162-8828", "1939-3539", "2160-9292"],
        "host_organization_name": "IEEE Computer Society",
        "homepage_url": "http://www.computer.org/tpami",
        "works_count": 12000,
        "cited_by_count": 900000,
        "summary_stats": {"h_index": 600, "2yr_mean_citedness": 18.456},
        "is_oa": False,
        "is_in_doaj": False,
        "apc_usd": 2495,
        "topics": [
            {"count": 900, "subfield": {"id": "https://openalex.org/subfields/1707"}, "field": {"display_name": "Computer Science"}},
            {"count": 100, "subfield": {"id": "https://openalex.org/subfields/1702"}, "field": {"display_name": "Computer Science"}},
        ],
    },
    "1532-4435": {
        "id": "https://openalex.org/S118988714",
        "display_name": "Journal of Machine Learning Research",
        "issn_l": "1532-4435",
        "issn": ["1532-4435", "1533-7928"],
        "host_organization_name": "Microtome Publishing",
        "homepage_url": "https://jmlr.org/",
        "works_count": 3000,
        "cited_by_count": 400000,
        "summary_stats": {"h_index": 300, "2yr_mean_citedness": 6.1},
        "is_oa": True,
        "is_in_doaj": True,
        "apc_usd": None,
        "topics": [
            {"count": 500, "subfield": {"id": "https://openalex.org/subfields/1702"}, "field": {"display_name": "Computer Science"}},
            {"count": 100, "subfield": {"id": "https://openalex.org/subfields/2613"}, "field": {"display_name": "Mathematics"}},
        ],
    },
    # Matches the broad subfield filter through a few electronics papers,
    # but is mostly chemistry: must never be listed.
    "1111-2222": {
        "id": "https://openalex.org/S1",
        "display_name": "Advanced Chemistry Letters",
        "issn_l": "1111-2222",
        "issn": ["1111-2222"],
        "host_organization_name": "Chem Press",
        "homepage_url": "https://chem.example.org",
        "works_count": 9000,
        "cited_by_count": 50000,
        "summary_stats": {"h_index": 700, "2yr_mean_citedness": 9.0},
        "is_oa": False,
        "is_in_doaj": False,
        "apc_usd": None,
        "topics": [
            {"count": 50, "subfield": {"id": "https://openalex.org/subfields/2208"}, "field": {"display_name": "Engineering"}},
            {"count": 950, "subfield": {"id": "https://openalex.org/subfields/1605"}, "field": {"display_name": "Chemistry"}},
        ],
    },
}


@pytest.fixture()
def journal_sources(monkeypatch, tmp_path):
    state = {"sjr": SJR_CSV, "sjr_calls": 0, "oa_fail": False, "oa_calls": []}

    def fake_download(url, timeout, max_bytes):
        state["sjr_calls"] += 1
        if state["sjr"] is None:
            raise OSError("403 Forbidden (bot challenge)")
        return state["sjr"].encode()

    def fake_openalex(path, params):
        state["oa_calls"].append(params)
        if state["oa_fail"]:
            raise catalog.CatalogUnavailableError("OpenAlex down")
        flt = params["filter"]
        if "issn:" in flt:
            wanted = flt.split("issn:")[1].split(",")[0].split("|")
            found = {id(v): v for i in wanted for k, v in OPENALEX.items() if i in v["issn"]}
            results = list(found.values())
        else:
            results = list(OPENALEX.values())
            if params.get("search"):
                results = [r for r in results if params["search"].lower() in r["display_name"].lower()]
        return {"meta": {"count": len(results)}, "results": results}

    monkeypatch.setattr(catalog, "_download", fake_download)
    monkeypatch.setattr(catalog, "_openalex_get", fake_openalex)
    monkeypatch.setattr(catalog, "SJR_CACHE_FILE", tmp_path / "sjr.json")
    monkeypatch.setattr(catalog, "SJR_MANUAL_FILE", tmp_path / "scimagojr.csv")
    catalog.reset_cache()
    yield state
    catalog.reset_cache()


def _when(days):
    return (datetime.now(timezone.utc) + timedelta(days=days)).replace(microsecond=0).isoformat()


# --- parsing -------------------------------------------------------------------


def test_issn_and_title_helpers():
    assert catalog.normalize_issn("15324435") == "1532-4435"
    assert catalog.normalize_issn("2049-136x") == "2049-136X"
    assert catalog.normalize_issn(" 1532-4435 ") == "1532-4435"
    assert catalog.normalize_issn("nonsense") is None
    assert catalog.title_key("Journal of Machine-Learning  Research!") == "journal of machine learning research"
    assert catalog.title_key("Science & Society") == "science and society"


def test_parse_sjr_csv():
    journals = catalog.parse_sjr_csv(SJR_CSV)
    assert [j["title"] for j in journals] == [
        "IEEE Transactions on Pattern Analysis and Machine Intelligence",
        "Journal of Machine Learning Research",
        "Regional Computing Letters",
        "Annals of Algebra",
        "IEEE Journal of Solid-State Circuits",
        "IEEE Micro",
    ]  # the proceedings row is skipped
    tpami = journals[0]
    assert tpami["issn"] == "1939-3539" and tpami["issns"] == ["1939-3539", "0162-8828"]
    assert tpami["sjr"] == pytest.approx(20.123)  # decimal comma
    assert tpami["sjr_quartile"] == "Q1" and tpami["h_index"] == 512 and tpami["sjr_rank"] == 1
    assert tpami["categories"][1] == {"name": "Computer Vision and Pattern Recognition", "quartile": "Q1"}
    assert tpami["areas"] == ["Computer Science", "Mathematics"]
    assert journals[1]["sjr_open_access"] is True
    assert journals[2]["issn"] == "2049-136X"

    with pytest.raises(ValueError):
        catalog.parse_sjr_csv("<html>Just a moment...</html>")


def test_lab_domains_and_filter_sjr():
    snapshot = catalog.SjrSnapshot(catalog.parse_sjr_csv(SJR_CSV), datetime.now(timezone.utc), "manual")
    journals = snapshot.journals
    domains = {j["title"]: j["domains"] for j in journals}
    assert domains["IEEE Transactions on Pattern Analysis and Machine Intelligence"] == ["ai", "cs_other"]
    assert domains["IEEE Journal of Solid-State Circuits"] == ["electronics"]  # Engineering area, EEE category
    assert domains["IEEE Micro"] == ["architecture", "cs_other"]
    assert domains["Regional Computing Letters"] == ["cs_other"]
    assert domains["Annals of Algebra"] == []  # pure mathematics: outside the lab

    titles = lambda rows: [r["title"] for r in rows]  # noqa: E731
    # The default listing is already restricted to lab domains.
    assert "Annals of Algebra" not in titles(catalog.filter_sjr(journals))
    assert len(catalog.filter_sjr(journals)) == 5
    assert catalog.filter_sjr(journals, q="algebra") == []
    assert catalog.filter_sjr(journals, q="0003-4444") == []
    assert titles(catalog.filter_sjr(journals, domain="architecture")) == ["IEEE Micro"]
    assert titles(catalog.filter_sjr(journals, domain="electronics")) == ["IEEE Journal of Solid-State Circuits"]
    assert len(catalog.filter_sjr(journals, domain="ai")) == 2
    assert titles(catalog.filter_sjr(journals, quartile="q4")) == ["Regional Computing Letters"]
    # Category names are searchable ("Artificial Intelligence" journals).
    assert len(catalog.filter_sjr(journals, q="artificial intelligence")) == 2
    assert titles(catalog.filter_sjr(journals, q="0162-8828")) == [
        "IEEE Transactions on Pattern Analysis and Machine Intelligence"
    ]
    assert titles(catalog.filter_sjr(journals, sort="title"))[0] == "IEEE Journal of Solid-State Circuits"
    assert titles(catalog.filter_sjr(journals, sort="h_index"))[1] == "IEEE Journal of Solid-State Circuits"


def test_openalex_domain_classification():
    tpami = catalog.normalize_openalex(OPENALEX["0162-8828"])
    assert tpami["domains"] == ["ai"] and tpami["lab_share"] == 1.0
    chem = catalog.normalize_openalex(OPENALEX["1111-2222"])
    assert chem["lab_share"] == 0.05 and chem["domains"] == []
    mixed, share = catalog.openalex_domains(
        [
            {"count": 40, "subfield": {"id": "https://openalex.org/subfields/1708"}},
            {"count": 35, "subfield": {"id": "https://openalex.org/subfields/2208"}},
            {"count": 25, "subfield": {"id": "https://openalex.org/subfields/3104"}},
        ]
    )
    assert mixed == ["architecture", "electronics"] and share == 0.75


def test_sjr_cache_manual_file_and_backoff(journal_sources):
    # Download blocked and nothing cached: SJR is simply unavailable.
    journal_sources["sjr"] = None
    assert catalog.get_sjr() is None
    calls = journal_sources["sjr_calls"]
    assert catalog.get_sjr() is None
    assert journal_sources["sjr_calls"] == calls  # cooldown: no retry yet

    # A CSV saved by hand is picked up and cached.
    catalog.SJR_MANUAL_FILE.write_text(SJR_CSV, encoding="utf-8")
    snapshot = catalog.get_sjr()
    assert snapshot.origin == "manual" and len(snapshot.journals) == 6
    assert catalog.SJR_CACHE_FILE.exists()

    # A new process reuses the disk cache without downloading.
    catalog.reset_cache()
    catalog.SJR_MANUAL_FILE.unlink()
    calls = journal_sources["sjr_calls"]
    assert len(catalog.get_sjr().journals) == 6
    assert journal_sources["sjr_calls"] == calls

    # Forced refresh failing keeps the cached copy.
    assert catalog.get_sjr(force_refresh=True) is not None


# --- API: browse ---------------------------------------------------------------


def test_browse_sjr_mode_with_enrichment(journal_sources, login, student, client):
    assert client.get(f"{J}/catalog").status_code == 401
    body = login(student).get(f"{J}/catalog").json()
    assert body["mode"] == "sjr" and body["ranking_available"] is True and body["total"] == 5
    assert body["total_is_estimate"] is False
    assert body["ranking"]["name"].startswith("SCImago") and body["metadata"]["license"] == "CC0"
    assert [d["id"] for d in body["domains"]] == ["architecture", "electronics", "ai", "cs_other"]
    assert "Annals of Algebra" not in [i["title"] for i in body["items"]]

    tpami, jmlr = body["items"][:2]
    regional = next(i for i in body["items"] if i["title"] == "Regional Computing Letters")
    assert tpami["sjr_quartile"] == "Q1" and tpami["h_index"] == 512
    assert tpami["homepage_url"] == "http://www.computer.org/tpami"
    assert tpami["two_year_mean_citedness"] == 18.46 and tpami["apc_usd"] == 2495
    assert tpami["enriched"] is True and tpami["submission_mode"] == "rolling"
    assert tpami["sjr_url"].endswith("q=21100&tip=sid")
    assert tpami["wikicfp_url"].startswith("http://www.wikicfp.com/cfp/servlet/tool.search?q=IEEE+Transactions")
    assert "special+issue+call+for+papers" in tpami["google_special_issues_url"]
    assert jmlr["is_oa"] is True and jmlr["is_in_doaj"] is True
    assert regional["enriched"] is False and regional["homepage_url"] is None

    # The whole page is enriched with a single OpenAlex request.
    assert len(journal_sources["oa_calls"]) == 1

    q1 = login(student).get(f"{J}/catalog", params={"quartile": "Q1", "sort": "title"}).json()
    assert [i["title"] for i in q1["items"]][0] == "IEEE Journal of Solid-State Circuits"
    arch = login(student).get(f"{J}/catalog", params={"domain": "architecture"}).json()
    assert [i["title"] for i in arch["items"]] == ["IEEE Micro"] and arch["items"][0]["domains"] == ["architecture", "cs_other"]
    assert login(student).get(f"{J}/catalog", params={"domain": "biology"}).status_code == 422


def test_browse_survives_openalex_outage(journal_sources, login, student):
    journal_sources["oa_fail"] = True
    body = login(student).get(f"{J}/catalog").json()
    assert body["total"] == 5 and body["metadata"]["available"] is False
    assert all(i["enriched"] is False for i in body["items"])


def test_browse_falls_back_to_openalex_without_sjr(journal_sources, login, student):
    journal_sources["sjr"] = None
    body = login(student).get(f"{J}/catalog", params={"quartile": "Q1"}).json()
    assert body["mode"] == "openalex" and body["ranking_available"] is False
    # The chemistry journal matches the broad OpenAlex filter but is dropped.
    assert body["total"] == 2 and body["total_is_estimate"] is False
    params = journal_sources["oa_calls"][-1]
    assert "topics.subfield.id:" in params["filter"] and "2208" in params["filter"]
    assert login(student).post(f"{J}/catalog/1111-2222/add").status_code == 404
    body = login(student).get(f"{J}/catalog", params={"q": "machine", "domain": "ai"}).json()
    assert "scimagojr.csv" in body["ranking"]["note"]
    assert [i["title"] for i in body["items"]] == [
        "IEEE Transactions on Pattern Analysis and Machine Intelligence",
        "Journal of Machine Learning Research",
    ]
    assert body["items"][0]["sjr_quartile"] is None and body["items"][0]["h_index"] == 600

    # Adding still works with OpenAlex data only.
    added = login(student).post(f"{J}/catalog/1532-4435/add")
    assert added.status_code == 201 and added.json()["sjr_quartile"] is None

    # No SJR and OpenAlex down: a clear 503.
    journal_sources["oa_fail"] = True
    assert login(student).get(f"{J}/catalog", params={"q": "other"}).status_code == 503


def test_add_from_catalog_and_dedup(journal_sources, login, student, make_project):
    api = login(student)
    project = make_project(student)

    created = api.post(f"{J}/catalog/0162-8828/add")
    assert created.status_code == 201, created.text
    journal = created.json()
    assert journal["title"].startswith("IEEE Transactions on Pattern")
    assert journal["issn"] == "1939-3539" and journal["sjr_quartile"] == "Q1"
    assert journal["sjr"] == pytest.approx(20.123) and journal["h_index"] == 512
    assert journal["homepage_url"] == "http://www.computer.org/tpami"
    assert journal["subject_areas"] == ["Computer Science", "Mathematics"]
    assert journal["submission_deadline"] is None and journal["seconds_remaining"] is None
    assert "Artificial Intelligence (Q1)" in journal["notes"] and "APC: US$2495" in journal["notes"]

    # Same journal through its other ISSN: reused, optionally linked to a project.
    again = api.post(f"{J}/catalog/19393539/add", json={"project_id": str(project.id)})
    assert again.status_code == 200 and again.json()["id"] == journal["id"]
    assert again.json()["linked_existing"] is True and again.json()["project_title"] == project.title

    items = {i["title"]: i for i in api.get(f"{J}/catalog").json()["items"]}
    tpami = items["IEEE Transactions on Pattern Analysis and Machine Intelligence"]
    assert tpami["in_my_list"] is True and tpami["my_journal_id"] == journal["id"]
    assert items["Journal of Machine Learning Research"]["in_my_list"] is False

    # A manually added journal with the same title counts as in the list.
    api.post(J, json={"title": "journal of machine learning research"})
    jmlr = api.post(f"{J}/catalog/1532-4435/add")
    assert jmlr.status_code == 200 and jmlr.json()["title"] == "journal of machine learning research"

    assert api.post(f"{J}/catalog/9999-9999/add").status_code == 404
    assert api.post(f"{J}/catalog/not-an-issn/add").status_code == 404


# --- API: my list ----------------------------------------------------------------


def test_journal_crud_special_issue_and_privacy(login, student, make_user):
    api = login(student)
    rolling = api.post(J, json={"title": "Pattern Recognition", "issn": "00313203", "sjr_quartile": "Q1"})
    assert rolling.status_code == 201, rolling.text
    assert rolling.json()["issn"] == "0031-3203"

    special = api.post(
        J,
        json={
            "title": "Neural Networks",
            "special_issue_title": "Foundation models",
            "submission_deadline": _when(10),
        },
    ).json()
    assert special["seconds_remaining"] > 0 and special["is_overdue"] is False
    api.post(J, json={"title": "Old Special", "submission_deadline": _when(-2)})

    # Upcoming special issues first, then rolling, then passed deadlines.
    assert [j["title"] for j in api.get(J).json()["items"]] == ["Neural Networks", "Pattern Recognition", "Old Special"]
    assert [j["title"] for j in api.get(J, params={"deadline": "rolling"}).json()["items"]] == ["Pattern Recognition"]
    assert api.get(J, params={"search": "foundation"}).json()["total"] == 1

    # Duplicates by ISSN or title are rejected.
    assert api.post(J, json={"title": "PR journal", "issn": "0031-3203"}).status_code == 409
    assert api.post(J, json={"title": "pattern  recognition"}).status_code == 409

    updated = api.patch(f"{J}/{rolling.json()['id']}", json={"special_issue_title": "Graph learning", "submission_deadline": _when(3)})
    assert updated.status_code == 200 and updated.json()["special_issue_title"] == "Graph learning"
    cleared = api.patch(f"{J}/{rolling.json()['id']}", json={"special_issue_title": None, "submission_deadline": None})
    assert cleared.json()["submission_deadline"] is None

    assert api.post(J, json={"title": "Bad", "issn": "12-34"}).status_code == 422
    assert api.post(J, json={"title": "Naive", "submission_deadline": "2027-05-01T12:00:00"}).status_code == 422

    # Lists are private.
    other = login(make_user("Student"))
    assert other.get(J).json()["total"] == 0
    assert other.get(f"{J}/{special['id']}").status_code == 404
    assert other.delete(f"{J}/{special['id']}").status_code == 404

    assert api.delete(f"{J}/{special['id']}").status_code == 200
    assert api.get(f"{J}/{special['id']}").status_code == 404


def test_project_link_requires_access(login, student, make_user, make_project):
    project = make_project(student)
    outsider = login(make_user("Student"))
    assert outsider.post(J, json={"title": "Some Journal", "project_id": str(project.id)}).status_code == 404
    linked = login(student).post(J, json={"title": "Some Journal", "project_id": str(project.id)})
    assert linked.status_code == 201 and linked.json()["project_title"] == project.title


def test_guest_is_read_only(journal_sources, login, guest):
    api = login(guest)
    assert api.get(J).status_code == 200
    assert api.get(f"{J}/catalog").status_code == 200
    assert api.post(J, json={"title": "Guest Journal"}).status_code == 403
    assert api.post(f"{J}/catalog/0162-8828/add").status_code == 403
