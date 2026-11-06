from datetime import date, timedelta

H = "/api/v1/handbook"
TODAY = date.today().isoformat()


def _entry(project, entry_date=TODAY, **overrides):
    payload = {
        "project_id": str(project.id),
        "entry_date": entry_date,
        "work_completed": "Ran baseline",
        "research_progress": "Accuracy 81%",
        "problems": "",
        "next_steps": "Tune",
        "references": ["https://arxiv.org/abs/1234.5678"],
    }
    payload.update(overrides)
    return payload


def _setup(make_user, make_project):
    professor = make_user("Professor")
    student = make_user("Student")
    peer = make_user("Student")
    project = make_project(student, members=[(professor, "supervisor"), (peer, "member")])
    return professor, student, peer, project


def test_one_entry_per_project_per_day(login, make_user, make_project):
    professor, student, peer, project = _setup(make_user, make_project)
    other_project = make_project(student, title="Second")
    api = login(student)
    assert api.post(f"{H}/entries", json=_entry(project)).status_code == 201
    assert api.post(f"{H}/entries", json=_entry(project)).status_code == 409
    # Same day, different project is allowed; so is another student.
    assert api.post(f"{H}/entries", json=_entry(other_project)).status_code == 201
    assert login(peer).post(f"{H}/entries", json=_entry(project)).status_code == 201


def test_entry_rules(login, make_user, make_project):
    professor, student, peer, project = _setup(make_user, make_project)
    api = login(student)
    future = (date.today() + timedelta(days=5)).isoformat()
    assert api.post(f"{H}/entries", json=_entry(project, entry_date=future)).status_code == 400
    empty = _entry(project, work_completed="", research_progress="", next_steps="")
    assert api.post(f"{H}/entries", json=empty).status_code == 422
    assert login(professor).post(f"{H}/entries", json=_entry(project)).status_code == 403
    outsider = make_user("Student")
    assert login(outsider).post(f"{H}/entries", json=_entry(project)).status_code == 404


def test_edit_history_preserved(login, make_user, make_project):
    professor, student, peer, project = _setup(make_user, make_project)
    api = login(student)
    entry = api.post(f"{H}/entries", json=_entry(project)).json()
    updated = api.patch(f"{H}/entries/{entry['id']}", json={"research_progress": "Accuracy 85%"}).json()
    assert updated["version"] == 2

    versions = api.get(f"{H}/entries/{entry['id']}/versions").json()
    assert [v["version"] for v in versions] == [2, 1]
    assert versions[1]["snapshot"]["research_progress"] == "Accuracy 81%"
    # Supervisors can read history too.
    assert len(login(professor).get(f"{H}/entries/{entry['id']}/versions").json()) == 2


def test_professor_comments_but_cannot_edit(login, make_user, make_project):
    professor, student, peer, project = _setup(make_user, make_project)
    entry = login(student).post(f"{H}/entries", json=_entry(project)).json()
    prof_api = login(professor)

    assert prof_api.patch(f"{H}/entries/{entry['id']}", json={"problems": "x"}).status_code == 403
    commented = prof_api.post(f"{H}/entries/{entry['id']}/comments", json={"body": "Add ablation"})
    assert commented.status_code == 201
    comment_id = commented.json()["comments"][0]["id"]

    # The student can edit after receiving comments and reply.
    student_api = login(student)
    assert student_api.patch(f"{H}/entries/{entry['id']}", json={"next_steps": "Ablation"}).status_code == 200
    replied = student_api.post(f"{H}/entries/{entry['id']}/comments", json={"body": "Done", "parent_id": comment_id})
    assert replied.json()["comments"][0]["replies"][0]["body"] == "Done"

    # Students cannot start comment threads; replies cannot nest further.
    assert student_api.post(f"{H}/entries/{entry['id']}/comments", json={"body": "Hi"}).status_code == 403
    reply_id = replied.json()["comments"][0]["replies"][0]["id"]
    assert prof_api.post(f"{H}/entries/{entry['id']}/comments", json={"body": "x", "parent_id": reply_id}).status_code == 400


def test_entry_visibility(login, make_user, make_project, admin):
    professor, student, peer, project = _setup(make_user, make_project)
    entry = login(student).post(f"{H}/entries", json=_entry(project)).json()

    assert login(peer).get(f"{H}/entries/{entry['id']}").status_code == 404
    assert login(make_user("Professor")).get(f"{H}/entries/{entry['id']}").status_code == 404
    assert login(professor).get(f"{H}/entries/{entry['id']}").status_code == 200
    assert login(admin).get(f"{H}/entries/{entry['id']}").status_code == 200

    listing = login(professor).get(f"{H}/entries", params={"project_id": str(project.id), "student_id": str(student.id)}).json()
    assert listing["total"] == 1
    assert login(peer).get(f"{H}/entries").json()["total"] == 0


def test_progress_by_date(login, make_user, make_project):
    professor, student, peer, project = _setup(make_user, make_project)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    login(student).post(f"{H}/entries", json=_entry(project))
    login(student).post(f"{H}/entries", json=_entry(project, entry_date=yesterday))
    login(peer).post(f"{H}/entries", json=_entry(project))
    days = login(professor).get(f"{H}/progress", params={"project_id": str(project.id)}).json()
    by_day = {d["entry_date"]: d for d in days}
    assert by_day[TODAY]["student_count"] == 2 and by_day[yesterday]["entry_count"] == 1


def test_daily_summary_private_and_unique(login, make_user, admin):
    student = make_user("Student")
    api = login(student)
    summary = api.post(f"{H}/summaries", json={"entry_date": TODAY, "summary": "Good day"})
    assert summary.status_code == 201
    assert api.post(f"{H}/summaries", json={"entry_date": TODAY, "summary": "Again"}).status_code == 409

    updated = api.patch(f"{H}/summaries/{summary.json()['id']}", json={"challenges": "GPU queue"}).json()
    assert updated["version"] == 2
    assert len(api.get(f"{H}/summaries/{summary.json()['id']}/versions").json()) == 2

    for other in (admin, make_user("Professor"), make_user("Student")):
        other_api = login(other)
        assert other_api.get(f"{H}/summaries").json()["total"] == 0
        assert other_api.patch(f"{H}/summaries/{summary.json()['id']}", json={"summary": "x"}).status_code == 404
        assert other_api.get(f"{H}/summaries/{summary.json()['id']}/versions").status_code == 404


def test_archived_project_entries_read_only(login, make_user, make_project):
    professor, student, peer, project = _setup(make_user, make_project)
    entry = login(student).post(f"{H}/entries", json=_entry(project)).json()
    login(professor).post(f"/api/v1/projects/{project.id}/archive")
    assert login(student).patch(f"{H}/entries/{entry['id']}", json={"problems": "x"}).status_code == 403
    assert login(professor).post(f"{H}/entries/{entry['id']}/comments", json={"body": "x"}).status_code == 403
    assert login(student).get(f"{H}/entries/{entry['id']}").status_code == 200
