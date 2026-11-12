R = "/api/v1/research"


def _paper(**overrides):
    payload = {
        "title": "Deep spectral unmixing",
        "authors": ["A. Rao", "B. Chen"],
        "abstract": "We study unmixing.",
        "publication_year": 2023,
        "venue": "CVPR",
        "doi": "https://doi.org/10.1234/ABC.5678",
        "url": "https://example.org/paper",
        "keywords": ["unmixing", "hyperspectral"],
    }
    payload.update(overrides)
    return payload


def test_create_paper_normalizes_doi(login, student):
    response = login(student).post(f"{R}/papers", json=_paper())
    assert response.status_code == 201, response.text
    assert response.json()["doi"] == "10.1234/abc.5678"


def test_invalid_doi_and_url_rejected(login, student):
    api = login(student)
    assert api.post(f"{R}/papers", json=_paper(doi="not-a-doi")).status_code == 422
    assert api.post(f"{R}/papers", json=_paper(doi=None, url="ftp://bad")).status_code == 422


def test_duplicate_doi_links_existing_instead_of_duplicating(login, student, make_project):
    project_a = make_project(student, title="A")
    project_b = make_project(student, title="B")
    api = login(student)

    first = api.post(f"{R}/papers", json=_paper(project_id=str(project_a.id))).json()
    assert api.post(f"{R}/papers", json=_paper(doi="10.1234/abc.5678")).status_code == 409

    second = api.post(f"{R}/papers", json=_paper(doi="10.1234/ABC.5678", project_id=str(project_b.id)))
    assert second.status_code == 200
    assert second.json()["id"] == first["id"]
    assert second.json()["linked_existing"] is True
    assert {p["title"] for p in second.json()["projects"]} == {"A", "B"}


def test_guest_cannot_add_or_browse_library(login, guest, student, make_project):
    project = make_project(student, members=[(guest, "guest")])
    paper = login(student).post(f"{R}/papers", json=_paper()).json()
    linked = login(student).post(f"{R}/papers", json=_paper(doi="10.1000/linked", url=None, project_id=str(project.id))).json()

    api = login(guest)
    assert api.post(f"{R}/papers", json=_paper(doi="10.9000/x")).status_code == 403
    visible = {item["id"] for item in api.get(f"{R}/papers").json()["items"]}
    assert linked["id"] in visible and paper["id"] not in visible
    assert api.get(f"{R}/papers/{paper['id']}").status_code == 404


def test_search_and_filters(login, student, make_project):
    project = make_project(student)
    api = login(student)
    api.post(f"{R}/papers", json=_paper(title="Graph transformers", authors=["Zed Q"], doi="10.1000/a", url=None, publication_year=2020, project_id=str(project.id)))
    api.post(f"{R}/papers", json=_paper(title="Old optics", authors=["Mia K"], doi="10.1000/b", url=None, publication_year=1999))

    def ids(**params):
        return [p["title"] for p in api.get(f"{R}/papers", params=params).json()["items"]]

    assert ids(search="graph") == ["Graph transformers"]
    assert ids(author="mia") == ["Old optics"]
    assert ids(year=1999) == ["Old optics"]
    assert ids(year_from=2000, year_to=2021) == ["Graph transformers"]
    assert ids(project_id=str(project.id)) == ["Graph transformers"]


def test_link_and_unlink_permissions(login, student, professor, make_user, make_project):
    project = make_project(student, members=[(professor, "supervisor")])
    outsider = make_user("Student")
    paper = login(outsider).post(f"{R}/papers", json=_paper()).json()

    # Non-members cannot link to the project.
    assert login(outsider).post(f"{R}/papers/{paper['id']}/projects", json={"project_id": str(project.id)}).status_code == 404

    assert login(student).post(f"{R}/papers/{paper['id']}/projects", json={"project_id": str(project.id)}).status_code == 200
    assert login(student).post(f"{R}/papers/{paper['id']}/projects", json={"project_id": str(project.id)}).status_code == 409
    assert login(professor).delete(f"{R}/papers/{paper['id']}/projects/{project.id}").status_code == 200
    # The central record survives removal of the association.
    assert login(student).get(f"{R}/papers/{paper['id']}").status_code == 200


def test_archived_project_blocks_linking(login, student, make_project):
    project = make_project(student, status="archived")
    paper = login(student).post(f"{R}/papers", json=_paper()).json()
    response = login(student).post(f"{R}/papers/{paper['id']}/projects", json={"project_id": str(project.id)})
    assert response.status_code == 403


def test_edit_metadata_permissions(login, student, professor, make_user):
    paper = login(student).post(f"{R}/papers", json=_paper()).json()
    other = make_user("Student")
    assert login(other).patch(f"{R}/papers/{paper['id']}", json={"title": "Hijack"}).status_code == 403
    assert login(professor).patch(f"{R}/papers/{paper['id']}", json={"title": "Corrected"}).json()["title"] == "Corrected"
    assert login(student).patch(f"{R}/papers/{paper['id']}", json={"publication_year": 2024}).json()["publication_year"] == 2024


def test_reading_progress_is_independent(login, make_user):
    a = make_user("Student")
    b = make_user("Student")
    paper = login(a).post(f"{R}/papers", json=_paper()).json()

    assert login(a).put(f"{R}/papers/{paper['id']}/progress", json={"status": "reading"}).status_code == 200
    assert login(a).put(f"{R}/papers/{paper['id']}/progress", json={"status": "completed"}).json()["status"] == "completed"
    assert login(b).get(f"{R}/papers/{paper['id']}").json()["my_status"] is None
    assert login(a).get(f"{R}/papers/{paper['id']}").json()["my_status"] == "completed"
    assert len(login(a).get(f"{R}/progress/me").json()) == 1
    assert login(a).get(f"{R}/papers", params={"reading_status": "completed"}).json()["total"] == 1
    assert login(b).get(f"{R}/papers", params={"reading_status": "not_started"}).json()["total"] >= 1


def test_every_library_user_tracks_own_progress_and_supervisor_sees_project_progress(
    login, student, professor, admin, guest, make_project
):
    project = make_project(student, members=[(professor, "supervisor"), (guest, "guest")])
    paper = login(student).post(f"{R}/papers", json=_paper(project_id=str(project.id))).json()
    # Professors and administrators keep their own reading status too.
    assert login(professor).put(f"{R}/papers/{paper['id']}/progress", json={"status": "completed"}).status_code == 200
    assert login(admin).put(f"{R}/papers/{paper['id']}/progress", json={"status": "reading"}).status_code == 200
    assert login(professor).get(f"{R}/papers/{paper['id']}").json()["my_status"] == "completed"
    assert login(student).get(f"{R}/papers/{paper['id']}").json()["my_status"] is None
    # Guests have no research library access.
    assert login(guest).put(f"{R}/papers/{paper['id']}/progress", json={"status": "reading"}).status_code == 403

    login(student).put(f"{R}/papers/{paper['id']}/progress", json={"status": "reading", "project_id": str(project.id)})
    rows = login(professor).get(f"{R}/projects/{project.id}/progress").json()
    student_rows = [row for row in rows if row["username"] == student.username]
    assert student_rows[0]["status"] == "reading"
    assert login(student).get(f"{R}/projects/{project.id}/progress").status_code == 403


def test_private_notes_hidden_from_everyone_else(login, student, admin, professor):
    paper = login(student).post(f"{R}/papers", json=_paper()).json()
    note = login(student).post(f"{R}/papers/{paper['id']}/notes", json={"content": "secret idea"}).json()

    assert login(student).get(f"{R}/papers/{paper['id']}/notes").json()[0]["content"] == "secret idea"
    for other in (admin, professor):
        api = login(other)
        assert api.get(f"{R}/papers/{paper['id']}/notes").json() == []
        assert api.patch(f"{R}/notes/{note['id']}", json={"content": "x"}).status_code == 404
        assert api.delete(f"{R}/notes/{note['id']}").status_code == 404

    assert login(student).patch(f"{R}/notes/{note['id']}", json={"content": "updated"}).json()["content"] == "updated"
    assert login(student).delete(f"{R}/notes/{note['id']}").status_code == 200


def test_delete_paper_removes_links_progress_and_notes(db, login, admin, student, make_project):
    from sqlalchemy import func, select

    from app.models.audit_log import AuditLog
    from app.models.research import PaperReadingProgress, ProjectPaper, ResearchNote, ResearchPaper

    project = make_project(student)
    api = login(student)
    paper = api.post(f"{R}/papers", json=_paper(project_id=str(project.id))).json()
    api.put(f"{R}/papers/{paper['id']}/progress", json={"status": "reading"})
    api.post(f"{R}/papers/{paper['id']}/notes", json={"content": "mine"})

    response = login(admin).delete(f"{R}/papers/{paper['id']}")
    assert response.status_code == 200, response.text

    def count(model, column):
        return db.scalar(select(func.count()).select_from(model).where(column == paper["id"]))

    assert db.get(ResearchPaper, paper["id"]) is None
    assert count(ProjectPaper, ProjectPaper.paper_id) == 0
    assert count(PaperReadingProgress, PaperReadingProgress.paper_id) == 0
    assert count(ResearchNote, ResearchNote.paper_id) == 0
    assert db.scalar(select(AuditLog).where(AuditLog.action == "paper.deleted", AuditLog.entity_id == paper["id"]))
    assert api.get(f"{R}/papers/{paper['id']}").status_code == 404
    assert login(admin).delete(f"{R}/papers/{paper['id']}").status_code == 404


def test_delete_paper_permissions(login, student, professor, make_user, make_project):
    other = make_user("Student")
    api = login(student)

    # Only people who can edit the paper may delete it.
    paper = api.post(f"{R}/papers", json=_paper()).json()
    assert login(other).delete(f"{R}/papers/{paper['id']}").status_code == 403

    # The adder cannot delete a paper a project uses, or one others wrote notes on.
    project = make_project(student)
    used = api.post(f"{R}/papers", json=_paper(doi="10.1000/used", url=None, project_id=str(project.id))).json()
    assert api.delete(f"{R}/papers/{used['id']}").status_code == 403
    login(other).post(f"{R}/papers/{paper['id']}/notes", json={"content": "their note"})
    assert api.delete(f"{R}/papers/{paper['id']}").status_code == 403

    # An unused paper can be deleted by the adder, and by a professor.
    own = api.post(f"{R}/papers", json=_paper(doi="10.1000/own", url=None)).json()
    api.post(f"{R}/papers/{own['id']}/notes", json={"content": "my own note"})
    assert api.delete(f"{R}/papers/{own['id']}").status_code == 200
    spare = api.post(f"{R}/papers", json=_paper(doi="10.1000/spare", url=None)).json()
    assert login(professor).delete(f"{R}/papers/{spare['id']}").status_code == 200


def test_delete_paper_requires_login_and_hides_from_guests(client, login, guest, student):
    paper = login(student).post(f"{R}/papers", json=_paper()).json()
    assert client.delete(f"{R}/papers/{paper['id']}").status_code == 401
    assert login(guest).delete(f"{R}/papers/{paper['id']}").status_code == 404
