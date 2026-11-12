"""GitHub repository links on projects."""

from datetime import date

from sqlalchemy import select

from app.models.audit_log import AuditLog

P = "/api/v1/projects"
REPO = "https://github.com/prism-lab/spectral-imaging"


def test_member_adds_link_and_url_is_normalised(login, student, professor, make_project, db):
    project = make_project(professor, members=[(student, "member")])
    api = login(student)

    response = api.post(f"{P}/{project.id}/repo-links", json={"url": REPO + ".git/", "label": "  Main code  "})
    assert response.status_code == 201, response.text
    link = response.json()
    assert link["url"] == REPO
    assert link["label"] == "Main code"
    assert link["added_by_username"] == student.username
    assert link["can_remove"] is True

    listed = login(professor).get(f"{P}/{project.id}/repo-links").json()
    assert [item["url"] for item in listed] == [REPO]
    assert listed[0]["can_remove"] is True  # professor manages the project

    audit = db.scalar(select(AuditLog).where(AuditLog.action == "project.repo_link_added"))
    assert audit.entity_id == str(project.id) and audit.details["url"] == REPO


def test_duplicate_link_rejected(login, student, make_project):
    project = make_project(student)
    api = login(student)
    assert api.post(f"{P}/{project.id}/repo-links", json={"url": REPO}).status_code == 201
    assert api.post(f"{P}/{project.id}/repo-links", json={"url": REPO + "/"}).status_code == 409


def test_only_github_https_links_accepted(login, student, make_project):
    project = make_project(student)
    api = login(student)
    for bad in (
        "http://github.com/a/b",
        "https://gitlab.com/a/b",
        "https://github.com/onlyowner",
        "https://github.com.evil.example/a/b",
        "javascript:alert(1)",
        "https://github.com/-bad/repo",
        "https://github.com/a/b c",
    ):
        assert api.post(f"{P}/{project.id}/repo-links", json={"url": bad}).status_code == 422, bad

    ok = api.post(f"{P}/{project.id}/repo-links", json={"url": "https://www.github.com/owner/repo/tree/main/src?x=1"})
    assert ok.status_code == 201
    assert ok.json()["url"] == "https://github.com/owner/repo/tree/main/src"


def test_guests_and_outsiders_cannot_add(login, student, guest, make_user, make_project):
    project = make_project(student, members=[(guest, "guest")])
    assert login(guest).get(f"{P}/{project.id}/repo-links").status_code == 200
    assert login(guest).post(f"{P}/{project.id}/repo-links", json={"url": REPO}).status_code == 403
    outsider = make_user("Student")
    assert login(outsider).post(f"{P}/{project.id}/repo-links", json={"url": REPO}).status_code == 404


def test_archived_project_is_read_only(login, student, make_project):
    project = make_project(student, status="archived")
    assert login(student).post(f"{P}/{project.id}/repo-links", json={"url": REPO}).status_code == 403


def test_remove_by_adder_or_manager_only(login, student, professor, make_user, make_project, db):
    other = make_user("Student")
    project = make_project(professor, members=[(student, "member"), (other, "member")])

    link = login(student).post(f"{P}/{project.id}/repo-links", json={"url": REPO}).json()
    assert login(other).get(f"{P}/{project.id}/repo-links").json()[0]["can_remove"] is False
    assert login(other).delete(f"{P}/{project.id}/repo-links/{link['id']}").status_code == 403
    assert login(student).delete(f"{P}/{project.id}/repo-links/{link['id']}").status_code == 200

    link = login(other).post(f"{P}/{project.id}/repo-links", json={"url": REPO}).json()
    assert login(professor).delete(f"{P}/{project.id}/repo-links/{link['id']}").status_code == 200
    assert login(professor).get(f"{P}/{project.id}/repo-links").json() == []
    assert db.scalar(select(AuditLog).where(AuditLog.action == "project.repo_link_removed")) is not None


def test_link_shows_on_dashboard_tiles(login, student, make_project):
    project = make_project(student)
    login(student).post(f"{P}/{project.id}/repo-links", json={"url": REPO, "label": "Code"})
    tiles = login(student).get("/api/v1/dashboard/student").json()["joined_projects"]
    assert tiles[0]["repo_links"] == [{"url": REPO, "label": "Code"}]
    assert tiles[0]["members"][0]["username"] == student.username


def test_dashboard_reading_list_heatmap_and_member_grid(login, student, professor, make_project):
    project = make_project(student, members=[(professor, "supervisor")])
    stu = login(student)
    first = stu.post(
        "/api/v1/research/papers", json={"title": "Alpha", "doi": "10.5555/alpha", "project_id": str(project.id)}
    ).json()
    stu.post("/api/v1/research/papers", json={"title": "Beta", "doi": "10.5555/beta", "project_id": str(project.id)})
    stu.put(f"/api/v1/research/papers/{first['id']}/progress", json={"status": "reading"})
    stu.post(
        "/api/v1/handbook/entries",
        json={"project_id": str(project.id), "entry_date": date.today().isoformat(), "work_completed": "x"},
    )

    data = stu.get("/api/v1/dashboard/student").json()
    assert data["reading_progress"]["counts"] == {"not_started": 1, "reading": 1, "completed": 0}
    assert [item["title"] for item in data["reading_list"]] == ["Alpha", "Beta"]
    assert data["reading_list"][0]["status"] == "reading"
    assert data["handbook_streak"] == 1
    assert data["handbook_days"][-1]["count"] == 1

    prof = login(professor).get("/api/v1/dashboard/professor").json()
    grid = {row["username"]: row for row in prof["member_reading"]}
    assert grid[student.username]["counts"]["reading"] == 1 and grid[student.username]["total"] == 2
    assert prof["my_reading"]["total"] == 2  # supervisor's own list: both project papers to read
    login(professor).put(f"/api/v1/research/papers/{first['id']}/progress", json={"status": "completed"})
    prof = login(professor).get("/api/v1/dashboard/professor").json()
    assert prof["my_reading"]["counts"]["completed"] == 1
    assert prof["reading_progress"]["counts"]["completed"] == 0  # members only, not the supervisor
