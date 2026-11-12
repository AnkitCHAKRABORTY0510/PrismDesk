"""Quick-add paper metadata lookup: input detection, source parsing and the endpoint.

All outbound HTTP goes through ``metadata_http.fetch``; tests swap its
transport for an ``httpx.MockTransport`` so no real network is used.
"""

import socket

import httpx
import pytest

from app.core.config import settings
from app.services import metadata_http, paper_metadata
from app.services.metadata_http import UnsafeUrlError
from app.services.paper_metadata import LookupInputError, detect, parse_arxiv, parse_html_meta, rebuild_abstract

R = "/api/v1/research"


CROSSREF_WORK = {
    "status": "ok",
    "message": {
        "DOI": "10.1109/CVPR.2023.01234",
        "title": ["Deep <i>spectral</i> unmixing"],
        "author": [{"given": "Asha", "family": "Rao"}, {"given": "Bo", "family": "Chen"}, {"name": "Prism Consortium"}],
        "container-title": ["2023 IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)"],
        "published-print": {"date-parts": [[2023, 6]]},
        "abstract": "<jats:title>Abstract</jats:title><jats:p>We study unmixing &amp; more.</jats:p>",
        "subject": ["Computer Vision"],
        "URL": "http://dx.doi.org/10.1109/cvpr.2023.01234",
    },
}

ARXIV_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v7</id>
    <published>2017-06-12T17:57:34Z</published>
    <title>Attention Is All
      You Need</title>
    <summary>  The dominant sequence transduction models...  </summary>
    <author><name>Ashish Vaswani</name></author>
    <author><name>Noam Shazeer</name></author>
    <category term="cs.CL" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cs.LG" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
</feed>"""

ARXIV_EMPTY = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>ArXiv Query</title></feed>"""

PAPER_PAGE = """<!doctype html><html><head>
<title>Site chrome | Journal</title>
<meta name="citation_title" content="Graph transformers for &amp; spectra">
<meta name="citation_author" content="Rao, Asha">
<meta name="citation_author" content="Chen, Bo">
<meta name="citation_journal_title" content="Journal of Imaging">
<meta name="citation_publication_date" content="2021/03/04">
<meta name="citation_keywords" content="graphs; spectra, imaging">
<meta property="og:description" content="Page abstract.">
</head><body>ignored</body></html>"""


@pytest.fixture()
def http(monkeypatch):
    """Route every metadata request to handlers keyed by host."""

    handlers: dict[str, object] = {}
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        handler = handlers.get(request.url.host)
        if handler is None:
            return httpx.Response(404)
        return handler(request)

    monkeypatch.setattr(metadata_http, "_transport", lambda: httpx.MockTransport(handle))
    # Hostnames resolve to a public address unless a test says otherwise.
    monkeypatch.setattr(metadata_http, "_resolve", lambda host, port: ["93.184.216.34"])
    handlers["calls"] = calls
    return handlers


def _crossref_ok(request):
    return httpx.Response(200, json=CROSSREF_WORK)


# --- Input detection ------------------------------------------------------


@pytest.mark.parametrize(
    "query, expected",
    [
        ("10.1109/CVPR.2023.01234", ("doi", "10.1109/cvpr.2023.01234")),
        ("  doi:10.1000/ABC  ", ("doi", "10.1000/abc")),
        ("DOI: 10.1000/xyz.", ("doi", "10.1000/xyz")),
        ("https://doi.org/10.1145/3292500.3330701", ("doi", "10.1145/3292500.3330701")),
        ("http://dx.doi.org/10.1000%2Fencoded", ("doi", "10.1000/encoded")),
        ("1706.03762", ("arxiv", "1706.03762")),
        ("arXiv:1706.03762v7", ("arxiv", "1706.03762v7")),
        ("2401.12345", ("arxiv", "2401.12345")),
        ("hep-th/9901001", ("arxiv", "hep-th/9901001")),
        ("math.GT/0309136v2", ("arxiv", "math.GT/0309136v2")),
        ("https://arxiv.org/abs/1706.03762v5", ("arxiv", "1706.03762v5")),
        ("https://arxiv.org/pdf/1706.03762.pdf", ("arxiv", "1706.03762")),
        ("http://export.arxiv.org/abs/hep-th/9901001", ("arxiv", "hep-th/9901001")),
        ("https://doi.org/10.48550/arXiv.2401.12345", ("arxiv", "2401.12345")),
        ("https://www.nature.com/articles/s41586-021-03819-2", ("url", "https://www.nature.com/articles/s41586-021-03819-2")),
        ("Attention is all you need", ("title", "Attention is all you need")),
    ],
)
def test_detect(query, expected):
    detected = detect(query)
    assert (detected.kind, detected.value) == expected


@pytest.mark.parametrize("query", ["", "   ", "short", "ftp://example.org/paper", "file:///etc/passwd"])
def test_detect_rejects_bad_input(query):
    with pytest.raises((LookupInputError, UnsafeUrlError)):
        detect(query)


# --- Parsers --------------------------------------------------------------


def test_parse_crossref_cleans_jats_and_names():
    data = paper_metadata.parse_crossref(CROSSREF_WORK["message"])
    assert data["title"] == "Deep spectral unmixing"
    assert data["authors"] == ["Asha Rao", "Bo Chen", "Prism Consortium"]
    assert data["abstract"] == "We study unmixing & more."
    assert data["publication_year"] == 2023
    assert data["venue"].endswith("(CVPR)")
    assert data["doi"] == "10.1109/cvpr.2023.01234"
    assert data["url"] == "https://doi.org/10.1109/cvpr.2023.01234"
    assert data["keywords"] == ["Computer Vision"]


def test_rebuild_openalex_abstract():
    assert rebuild_abstract({"world": [1], "Hello": [0], "again": [3], "hello": [2]}) == "Hello world hello again"
    assert rebuild_abstract(None) == ""


def test_parse_arxiv_entry():
    data = parse_arxiv(ARXIV_FEED, "1706.03762v7")
    assert data["title"] == "Attention Is All You Need"
    assert data["authors"] == ["Ashish Vaswani", "Noam Shazeer"]
    assert data["abstract"] == "The dominant sequence transduction models..."
    assert data["publication_year"] == 2017
    assert data["doi"] == "10.48550/arxiv.1706.03762"
    assert data["url"] == "https://arxiv.org/abs/1706.03762"
    assert data["keywords"] == ["cs.CL", "cs.LG"]
    assert data["venue"] == "arXiv"


def test_parse_arxiv_prefers_journal_doi_and_ref():
    feed = ARXIV_FEED.replace(
        "</summary>",
        "</summary><arxiv:doi>10.1000/Journal.1</arxiv:doi><arxiv:journal_ref>NeurIPS 2017</arxiv:journal_ref>",
    )
    data = parse_arxiv(feed, "1706.03762")
    assert data["doi"] == "10.1000/journal.1"
    assert data["arxiv_doi"] == "10.48550/arxiv.1706.03762"
    assert data["venue"] == "NeurIPS 2017"


def test_parse_arxiv_not_found():
    from app.core.errors import NotFoundError

    with pytest.raises(NotFoundError):
        parse_arxiv(ARXIV_EMPTY, "9999.99999")


def test_parse_html_meta():
    data = parse_html_meta(PAPER_PAGE, "https://journal.example/a/1")
    assert data["title"] == "Graph transformers for & spectra"
    assert data["authors"] == ["Rao, Asha", "Chen, Bo"]
    assert data["venue"] == "Journal of Imaging"
    assert data["publication_year"] == 2021
    assert data["keywords"] == ["graphs", "spectra", "imaging"]
    assert data["abstract"] == "Page abstract."
    assert data["doi"] is None
    assert data["url"] == "https://journal.example/a/1"


def test_parse_html_meta_falls_back_to_dc_and_og_tags():
    page = """<html><head><title>Fallback title</title>
    <meta name="DC.creator" content="Mia K"><meta name="DC.identifier" content="urn:isbn:123">
    <meta name="DC.identifier" content="doi:10.5555/DC.42"><meta name="dc.date" content="1999-01-01">
    </head></html>"""
    data = parse_html_meta(page, "https://x.example/")
    assert data["title"] == "Fallback title"
    assert data["authors"] == ["Mia K"]
    assert data["doi"] == "10.5555/dc.42"
    assert data["publication_year"] == 1999


# --- SSRF guard -----------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin",
        "http://localhost/",
        "http://10.0.0.5/",
        "http://192.168.1.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://user:pass@example.org/",
        "http://example.org:8080/",
    ],
)
def test_private_and_unusual_urls_are_blocked(url, monkeypatch):
    real = socket.getaddrinfo
    monkeypatch.setattr(
        metadata_http.socket,
        "getaddrinfo",
        lambda host, *a, **k: real("127.0.0.1", *a, **k) if host == "localhost" else real(host, *a, **k),
    )
    with pytest.raises(UnsafeUrlError):
        metadata_http.ensure_public_url(url)


def test_redirect_to_private_address_is_blocked(http, monkeypatch):
    monkeypatch.setattr(
        metadata_http, "_resolve", lambda host, port: ["10.0.0.7"] if host == "internal.example" else ["93.184.216.34"]
    )
    http["journal.example"] = lambda r: httpx.Response(302, headers={"location": "http://internal.example/secret"})
    with pytest.raises(UnsafeUrlError):
        paper_metadata.lookup_url("https://journal.example/paper")
    assert all(call.url.host != "internal.example" for call in http["calls"])


# --- Resolver with mocked services ---------------------------------------


def test_doi_uses_crossref_and_openalex_for_missing_abstract(http):
    work = {"message": {**CROSSREF_WORK["message"], "abstract": None, "subject": []}}
    http["api.crossref.org"] = lambda r: httpx.Response(200, json=work)
    http["api.openalex.org"] = lambda r: httpx.Response(
        200,
        json={
            "abstract_inverted_index": {"From": [0], "OpenAlex.": [1]},
            "keywords": [{"display_name": "Hyperspectral imaging"}],
        },
    )
    data = paper_metadata.resolve("doi:10.1109/CVPR.2023.01234")
    assert data["abstract"] == "From OpenAlex."
    assert data["keywords"] == ["Hyperspectral imaging"]
    assert data["matched_by"] == "doi" and data["source"] == "crossref"
    crossref = next(c for c in http["calls"] if c.url.host == "api.crossref.org")
    assert crossref.url.path == "/works/10.1109/cvpr.2023.01234"
    assert crossref.headers["user-agent"].startswith("PrismDesk/")


def test_non_crossref_doi_falls_back_to_doi_org(http):
    http["doi.org"] = lambda r: httpx.Response(
        200, json={"title": "A Zenodo dataset", "author": [{"literal": "Lab"}], "issued": {"date-parts": [[2022]]}}
    )
    data = paper_metadata.resolve("10.5281/zenodo.12345")
    assert data["title"] == "A Zenodo dataset" and data["source"] == "doi.org"
    assert data["doi"] == "10.5281/zenodo.12345"


def test_arxiv_lookup_sends_id(http):
    http["export.arxiv.org"] = lambda r: httpx.Response(200, text=ARXIV_FEED)
    data = paper_metadata.resolve("https://arxiv.org/abs/1706.03762v7")
    assert data["title"] == "Attention Is All You Need" and data["matched_by"] == "arxiv"
    request = next(c for c in http["calls"] if c.url.host == "export.arxiv.org")
    assert request.url.params["id_list"] == "1706.03762v7"


def test_web_page_with_doi_is_enriched_from_crossref(http):
    page = PAPER_PAGE.replace("</head>", '<meta name="citation_doi" content="10.1109/CVPR.2023.01234"></head>')
    http["journal.example"] = lambda r: httpx.Response(200, text=page, headers={"content-type": "text/html; charset=utf-8"})
    http["api.crossref.org"] = _crossref_ok
    data = paper_metadata.resolve("https://journal.example/a/1")
    assert data["title"] == "Deep spectral unmixing"  # Crossref wins over page tags
    assert data["url"] == "https://journal.example/a/1"  # but the pasted link is kept
    assert data["source"] == "webpage+crossref" and data["matched_by"] == "url"


def test_web_page_without_doi_uses_meta_tags(http):
    http["journal.example"] = lambda r: httpx.Response(200, text=PAPER_PAGE, headers={"content-type": "text/html"})
    data = paper_metadata.resolve("https://journal.example/a/1")
    assert data["title"] == "Graph transformers for & spectra" and data["source"] == "webpage"


def test_pdf_link_gives_helpful_error(http):
    http["files.example"] = lambda r: httpx.Response(200, content=b"%PDF-1.7 ...", headers={"content-type": "application/pdf"})
    with pytest.raises(LookupInputError, match="PDF"):
        paper_metadata.resolve("https://files.example/paper.pdf")


def test_title_search_picks_closest_title_among_top_hits(http):
    def search(request):
        assert request.url.params["query.bibliographic"] == "Deep spectral unmixing"
        assert request.url.params["rows"] == "5"
        survey = {**CROSSREF_WORK["message"], "DOI": "10.1000/survey", "title": ["Deep spectral unmixing: a survey of methods"]}
        return httpx.Response(200, json={"message": {"items": [survey, CROSSREF_WORK["message"]]}})

    http["api.crossref.org"] = search
    data = paper_metadata.resolve("Deep spectral unmixing")
    assert data["doi"] == "10.1109/cvpr.2023.01234" and data["matched_by"] == "title"


def test_title_search_without_close_match_is_not_found(http):
    from app.core.errors import NotFoundError

    unrelated = {**CROSSREF_WORK["message"], "title": ["Butterfly recognition in the wild"]}
    http["api.crossref.org"] = lambda r: httpx.Response(200, json={"message": {"items": [unrelated]}})
    with pytest.raises(NotFoundError):
        paper_metadata.resolve("Deep spectral unmixing")


# --- Endpoint -------------------------------------------------------------


def test_lookup_requires_login_and_capability(client, login, guest, http):
    assert client.get(f"{R}/lookup", params={"q": "10.1000/x"}).status_code == 401
    assert login(guest).get(f"{R}/lookup", params={"q": "10.1000/x"}).status_code == 403


def test_lookup_endpoint_flags_duplicates(login, student, http):
    http["api.crossref.org"] = _crossref_ok
    api = login(student)
    body = api.get(f"{R}/lookup", params={"q": "https://doi.org/10.1109/CVPR.2023.01234"}).json()
    assert body["title"] == "Deep spectral unmixing"
    assert body["matched_by"] == "doi" and body["source"] == "crossref"
    assert body["existing_paper_id"] is None

    created = api.post(f"{R}/papers", json={"title": body["title"], "doi": body["doi"]}).json()
    again = api.get(f"{R}/lookup", params={"q": "10.1109/cvpr.2023.01234"}).json()
    assert again["existing_paper_id"] == created["id"]


def test_lookup_flags_arxiv_duplicate_saved_under_arxiv_doi(login, student, http):
    feed = ARXIV_FEED.replace("</summary>", "</summary><arxiv:doi>10.1000/journal.1</arxiv:doi>")
    http["export.arxiv.org"] = lambda r: httpx.Response(200, text=feed)
    api = login(student)
    created = api.post(f"{R}/papers", json={"title": "Attention", "doi": "10.48550/arXiv.1706.03762"}).json()
    body = api.get(f"{R}/lookup", params={"q": "arXiv:1706.03762"}).json()
    assert body["doi"] == "10.1000/journal.1"
    assert body["existing_paper_id"] == created["id"]


def test_lookup_errors(login, student, http, monkeypatch):
    api = login(student)
    http["export.arxiv.org"] = lambda r: httpx.Response(200, text=ARXIV_EMPTY)
    assert api.get(f"{R}/lookup", params={"q": "10.1000/missing"}).status_code == 404  # Crossref + doi.org 404
    assert api.get(f"{R}/lookup", params={"q": "2401.99999"}).status_code == 404
    assert api.get(f"{R}/lookup", params={"q": "hmm"}).status_code == 422
    assert api.get(f"{R}/lookup").status_code == 422
    assert api.get(f"{R}/lookup", params={"q": "http://127.0.0.1:8000/api/v1/auth/me"}).status_code == 422

    # Older clients: ?doi= stays a strict DOI lookup.
    assert api.get(f"{R}/lookup", params={"doi": "not a doi"}).status_code == 422

    def offline(request):
        raise httpx.ConnectError("offline")

    def slow(request):
        raise httpx.ReadTimeout("slow")

    http["api.crossref.org"] = offline
    response = api.get(f"{R}/lookup", params={"doi": "10.1000/x"})
    assert response.status_code == 502 and "Crossref" in response.json()["detail"]
    http["api.crossref.org"] = slow
    assert api.get(f"{R}/lookup", params={"q": "10.1000/x"}).status_code == 504


def test_lookup_is_rate_limited(login, student, http, monkeypatch):
    monkeypatch.setattr(settings, "PAPER_LOOKUP_RATE_LIMIT", 2)
    http["api.crossref.org"] = _crossref_ok
    api = login(student)
    codes = [api.get(f"{R}/lookup", params={"q": "10.1000/x"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_csrf_flow_lookup_then_save(login, student, http):
    """Regression: "Missing or invalid CSRF token." when saving after Quick add.

    The lookup does not touch the token. The token is bound to the session
    cookie, so signing in again in the same browser makes a page's old
    token stale; /auth/me returns the current one, which the client uses
    to recover.
    """

    http["api.crossref.org"] = _crossref_ok
    api = login(student)
    first_token = api.csrf_token
    assert api.get(f"{R}/lookup", params={"q": "10.1109/CVPR.2023.01234"}).status_code == 200
    assert api.get("/api/v1/auth/me").json()["csrf_token"] == first_token

    paper = {"title": "Deep spectral unmixing", "doi": "10.1109/cvpr.2023.01234"}
    assert api.post(f"{R}/papers", json=paper, headers={"X-CSRF-Token": ""}).status_code == 403

    # Signing in again (e.g. in another tab) replaces the session cookie.
    from tests.conftest import TEST_PASSWORD

    relogin = api.post("/api/v1/auth/login", json={"identifier": student.username, "password": TEST_PASSWORD})
    assert relogin.status_code == 200
    stale = api.post(f"{R}/papers", json=paper, headers={"X-CSRF-Token": first_token})
    assert stale.status_code == 403 and stale.json()["detail"] == "Missing or invalid CSRF token."

    fresh = api.get("/api/v1/auth/me").json()["csrf_token"]
    assert fresh != first_token
    assert api.post(f"{R}/papers", json=paper, headers={"X-CSRF-Token": fresh}).status_code == 201
