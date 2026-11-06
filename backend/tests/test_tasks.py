from datetime import datetime, timedelta, timezone

T = "/api/v1/tasks"


def _due(days=3):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _official(project, assignees=(), **overrides):
    payload = {
        "task_type": "official",
        "title": "Literature survey",
        "description": "Survey 10 papers",
        "project_id": str(project.id),
        "priority": "high",
        "due_at": _due(),
        "assignee_ids": [str(user.id) for user in assignees],
    }
    payload.update(overrides)
    return payload


def _setup(make_user, make_project):
    professor = make_user("Professor")
    owner = make_user("Student")
    other = make_user("Student")
    project = make_project(owner, members=[(professor, "supervisor"), (other, "member")])
    return professor, owner, other, project


def test_only_supervisors_create_official_tasks(login, make_user, make_project):
    professor, owner, other, project = _setup(make_user, make_project)
    assert login(owner).post(T, json=_official(project)).status_code == 403
    unrelated_prof = make_user("Professor")
    assert login(unrelated_prof).post(T, json=_official(project)).status_code == 404
    response = login(professor).post(T, json=_official(project, [owner, other]))
    assert response.status_code == 201, response.text
    assert len(response.json()["assignments"]) == 2


def test_assignees_must_be_student_members(login, make_user, make_project):
    professor, owner, other, project = _setup(make_user, make_project)
    outsider = make_user("Student")
    assert login(professor).post(T, json=_official(project, [outsider])).status_code == 400
    assert login(professor).post(T, json=_official(project, [professor])).status_code == 400


def test_independent_assignment_status_and_privacy(login, make_user, make_project):
    professor, owner, other, project = _setup(make_user, make_project)
    task = login(professor).post(T, json=_official(project, [owner, other])).json()

    owner_api, other_api = login(owner), login(other)
    owner_view = owner_api.get(f"{T}/{task['id']}").json()
    assert [a["assignee"]["id"] for a in owner_view["assignments"]] == [str(owner.id)]
    my = owner_view["my_assignment"]

    other_assignment = other_api.get(f"{T}/{task['id']}").json()["my_assignment"]

    assert owner_api.patch(f"{T}/assignments/{my['id']}/status", json={"status": "in_progress"}).json()["status"] == "in_progress"
    assert other_api.get(f"{T}/{task['id']}").json()["my_assignment"]["status"] == "todo"

    # A student cannot read or act on another student's assignment.
    assert owner_api.get(f"{T}/assignments/{other_assignment['id']}/submissions").status_code == 404
    assert owner_api.post(f"{T}/assignments/{other_assignment['id']}/submissions", json={"response_text": "x"}).status_code == 404


def test_full_review_workflow_with_versions(login, make_user, make_project):
    professor, owner, other, project = _setup(make_user, make_project)
    task = login(professor).post(T, json=_official(project, [owner])).json()
    student_api, prof_api = login(owner), login(professor)
    assignment_id = student_api.get(f"{T}/{task['id']}").json()["my_assignment"]["id"]

    # Students cannot jump straight to review or completion.
    assert student_api.patch(f"{T}/assignments/{assignment_id}/status", json={"status": "completed"}).status_code == 409
    assert student_api.patch(f"{T}/assignments/{assignment_id}/status", json={"status": "under_review"}).status_code == 409

    student_api.patch(f"{T}/assignments/{assignment_id}/status", json={"status": "in_progress"})
    v1 = student_api.post(
        f"{T}/assignments/{assignment_id}/submissions",
        json={"response_text": "Draft", "links": ["https://github.com/lab/repo"]},
    )
    assert v1.status_code == 201 and v1.json()["version"] == 1
    assert student_api.post(f"{T}/assignments/{assignment_id}/submissions", json={"response_text": "again"}).status_code == 409

    pending = prof_api.get(f"{T}/reviews/pending").json()
    assert pending["total"] == 1 and pending["items"][0]["latest_version"] == 1

    assert student_api.post(f"{T}/submissions/{v1.json()['id']}/review", json={"decision": "approved"}).status_code == 403
    assert prof_api.post(f"{T}/submissions/{v1.json()['id']}/review", json={"decision": "revision_required"}).status_code == 422
    reviewed = prof_api.post(
        f"{T}/submissions/{v1.json()['id']}/review",
        json={"decision": "revision_required", "feedback": "Add baselines"},
    )
    assert reviewed.status_code == 200
    assert student_api.get(f"{T}/{task['id']}").json()["my_assignment"]["status"] == "revision_required"

    v2 = student_api.post(f"{T}/assignments/{assignment_id}/submissions", json={"response_text": "Final"}).json()
    assert v2["version"] == 2
    # Old versions can no longer be reviewed.
    assert prof_api.post(f"{T}/submissions/{v1.json()['id']}/review", json={"decision": "approved"}).status_code == 409
    prof_api.post(f"{T}/submissions/{v2['id']}/review", json={"decision": "approved", "feedback": "Good"})

    history = student_api.get(f"{T}/assignments/{assignment_id}/submissions").json()
    assert [s["version"] for s in history] == [2, 1]
    assert history[1]["reviews"][0]["feedback"] == "Add baselines"
    assert student_api.get(f"{T}/{task['id']}").json()["my_assignment"]["status"] == "completed"


def test_submission_validation_rejects_files_and_bad_links(login, make_user, make_project):
    professor, owner, other, project = _setup(make_user, make_project)
    task = login(professor).post(T, json=_official(project, [owner])).json()
    api = login(owner)
    assignment_id = api.get(f"{T}/{task['id']}").json()["my_assignment"]["id"]
    assert api.post(f"{T}/assignments/{assignment_id}/submissions", json={}).status_code == 422
    assert api.post(f"{T}/assignments/{assignment_id}/submissions", json={"links": ["javascript:alert(1)"]}).status_code == 422


def test_personal_tasks_are_private(login, make_user, make_project, admin):
    student = make_user("Student")
    api = login(student)
    task = api.post(T, json={"task_type": "personal", "title": "Read chapter 3", "due_at": _due(1)}).json()
    assignment = task["my_assignment"]

    assert api.patch(f"{T}/assignments/{assignment['id']}/status", json={"status": "completed"}).json()["status"] == "completed"
    assert api.post(f"{T}/assignments/{assignment['id']}/submissions", json={"response_text": "x"}).status_code == 400

    for other in (admin, make_user("Professor"), make_user("Student")):
        other_api = login(other)
        assert other_api.get(f"{T}/{task['id']}").status_code == 404
        assert all(t["id"] != task["id"] for t in other_api.get(T).json()["items"])

    assert login(make_user("Professor")).post(T, json={"task_type": "personal", "title": "x"}).status_code == 403
    assert api.delete(f"{T}/{task['id']}").status_code == 200


def test_filters_and_overdue(login, make_user, make_project):
    professor, owner, other, project = _setup(make_user, make_project)
    prof_api = login(professor)
    prof_api.post(T, json=_official(project, [owner], title="Late", due_at=_due(-2)))
    prof_api.post(T, json=_official(project, [owner], title="Soon", priority="low"))

    api = login(owner)
    assert [t["title"] for t in api.get(T, params={"overdue": True}).json()["items"]] == ["Late"]
    assert api.get(T, params={"priority": "low"}).json()["total"] == 1
    assert api.get(T, params={"status": "todo", "project_id": str(project.id)}).json()["total"] == 2
    assert api.get(T, params={"status": "completed"}).json()["total"] == 0
    assert prof_api.get(T, params={"scope": "managed"}).json()["total"] == 2
    late = api.get(T, params={"overdue": True}).json()["items"][0]
    assert late["is_overdue"] is True


def test_archived_project_tasks_are_read_only(login, make_user, make_project, db):
    professor, owner, other, project = _setup(make_user, make_project)
    task = login(professor).post(T, json=_official(project, [owner])).json()
    login(professor).post(f"/api/v1/projects/{project.id}/archive")
    api = login(owner)
    assignment_id = api.get(f"{T}/{task['id']}").json()["my_assignment"]["id"]
    assert api.patch(f"{T}/assignments/{assignment_id}/status", json={"status": "in_progress"}).status_code == 403
    assert login(professor).patch(f"{T}/{task['id']}", json={"title": "New"}).status_code == 403
