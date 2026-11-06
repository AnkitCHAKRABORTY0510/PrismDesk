from datetime import date, datetime, timedelta, timezone

D = "/api/v1/dashboard"


def _future(days):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def test_dashboard_authorization(login, admin, professor, student, guest, client):
    assert client.get(f"{D}/admin").status_code == 401
    assert login(admin).get(f"{D}/admin").status_code == 200
    for user, allowed in ((professor, "professor"), (student, "student"), (guest, "guest")):
        api = login(user)
        assert api.get(f"{D}/{allowed}").status_code == 200
        assert api.get(f"{D}/admin").status_code == 403
    assert login(student).get(f"{D}/professor").status_code == 403
    assert login(guest).get(f"{D}/student").status_code == 403
    assert login(student).get(f"{D}/system-settings").status_code == 403
    settings = login(admin).get(f"{D}/system-settings").json()
    assert "DISCORD_BOT_TOKEN" not in str(settings) and "password" not in str(settings).lower()


def test_admin_dashboard_counts_real_data(login, admin, make_user, make_project):
    make_user(status="pending")
    make_user("Student", status="suspended")
    owner = make_user("Student")
    make_project(owner)
    make_project(owner, status="archived")
    body = login(admin).get(f"{D}/admin").json()
    assert body["users"]["counts"]["pending"] >= 1
    assert body["users"]["counts"]["suspended"] >= 1
    assert body["projects"]["counts"]["active"] >= 1
    assert body["projects"]["counts"]["archived"] >= 1


def test_professor_and_student_dashboards(login, make_user, make_project):
    professor = make_user("Professor")
    student = make_user("Student")
    project = make_project(student, members=[(professor, "supervisor")])
    unrelated = make_project(make_user("Student"), title="Unrelated")

    prof_api, student_api = login(professor), login(student)
    task = prof_api.post(
        "/api/v1/tasks",
        json={"task_type": "official", "title": "Survey", "project_id": str(project.id), "due_at": _future(2), "assignee_ids": [str(student.id)]},
    ).json()
    assignment = student_api.get(f"/api/v1/tasks/{task['id']}").json()["my_assignment"]
    student_api.post(f"/api/v1/tasks/assignments/{assignment['id']}/submissions", json={"response_text": "done"})
    student_api.post("/api/v1/tasks", json={"task_type": "personal", "title": "Read"})
    student_api.post(
        "/api/v1/handbook/entries",
        json={"project_id": str(project.id), "entry_date": date.today().isoformat(), "work_completed": "x"},
    )
    paper = student_api.post(
        "/api/v1/research/papers", json={"title": "P", "doi": "10.5555/dash", "project_id": str(project.id)}
    ).json()
    student_api.put(f"/api/v1/research/papers/{paper['id']}/progress", json={"status": "completed"})

    prof = prof_api.get(f"{D}/professor").json()
    assert [p["id"] for p in prof["supervised_projects"]] == [str(project.id)]
    assert str(unrelated.id) not in str(prof)
    assert prof["pending_reviews"] == 1 and prof["review_queue"][0]["task_title"] == "Survey"
    assert prof["recent_handbook_entries"][0]["student_username"] == student.username
    assert prof["reading_progress"]["counts"]["completed"] == 1

    stu = student_api.get(f"{D}/student").json()
    assert stu["owned_project_count"] == 1
    assert stu["assigned_tasks"]["counts"]["under_review"] == 1
    assert stu["personal_tasks"]["counts"]["todo"] == 1
    assert stu["reading_progress"]["counts"]["completed"] == 1
    assert stu["handbook_entries_last_7_days"] == 1
    assert [d["title"] for d in stu["upcoming_deadlines"]] == ["Survey"]

    analytics = prof_api.get(f"{D}/projects/{project.id}").json()
    assert analytics["assignments"]["counts"]["under_review"] == 1
    assert analytics["paper_count"] == 1
    assert student_api.get(f"{D}/projects/{project.id}").status_code == 403


def test_guest_dashboard_only_shows_granted_projects(login, guest, make_user, make_project):
    owner = make_user("Student")
    granted = make_project(owner, members=[(guest, "guest")], title="Granted")
    make_project(owner, title="Hidden")
    body = login(guest).get(f"{D}/guest").json()
    assert [p["title"] for p in body["projects"]] == ["Granted"]
