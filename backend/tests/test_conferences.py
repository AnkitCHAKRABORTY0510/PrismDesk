from datetime import datetime, timedelta, timezone

C = "/api/v1/conferences"


def _when(days):
    return (datetime.now(timezone.utc) + timedelta(days=days)).replace(microsecond=0).isoformat()


def _conf(**overrides):
    payload = {
        "name": "NeurIPS 2027",
        "acronym": "NeurIPS",
        "website_url": "https://neurips.cc",
        "cfp_url": "https://neurips.cc/cfp",
        "submission_deadline": _when(30),
        "important_dates": [{"label": "Notification", "date": _when(90)}],
        "location": "Vancouver",
    }
    payload.update(overrides)
    return payload


def test_student_member_adds_conference_to_project(login, student, make_project):
    project = make_project(student)
    response = login(student).post(C, json=_conf(project_id=str(project.id)))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["projects"][0]["project_id"] == str(project.id)
    assert body["is_overdue"] is False and body["seconds_remaining"] > 0


def test_duplicate_conference_is_reused_across_projects(login, student, make_project):
    a = make_project(student, title="A")
    b = make_project(student, title="B")
    api = login(student)
    first = api.post(C, json=_conf(project_id=str(a.id))).json()
    second = api.post(C, json=_conf(name="neurips 2027", submission_deadline=first["submission_deadline"], project_id=str(b.id)))
    assert second.status_code == 200
    assert second.json()["id"] == first["id"] and second.json()["linked_existing"] is True
    assert len(second.json()["projects"]) == 2
    assert api.post(C, json=_conf(submission_deadline=first["submission_deadline"])).status_code == 409


def test_naive_timestamp_rejected(login, student):
    response = login(student).post(C, json=_conf(submission_deadline="2027-05-01T12:00:00"))
    assert response.status_code == 422


def test_non_member_cannot_link(login, student, make_user, make_project):
    project = make_project(student)
    outsider = make_user("Student")
    conference = login(outsider).post(C, json=_conf()).json()
    assert login(outsider).post(f"{C}/{conference['id']}/projects", json={"project_id": str(project.id)}).status_code == 404
    assert login(student).post(f"{C}/{conference['id']}/projects", json={"project_id": str(project.id)}).status_code == 200


def test_filters_sorting_and_overdue(login, student, make_project):
    project = make_project(student)
    api = login(student)
    api.post(C, json=_conf(name="Past Conf", submission_deadline=_when(-3), project_id=str(project.id)))
    api.post(C, json=_conf(name="Later Conf", submission_deadline=_when(40), project_id=str(project.id)))
    api.post(C, json=_conf(name="Soon Conf", submission_deadline=_when(5)))

    names = [c["name"] for c in api.get(C, params={"search": "conf"}).json()["items"]]
    assert names == ["Soon Conf", "Later Conf", "Past Conf"]
    assert [c["name"] for c in api.get(C, params={"timing": "overdue", "search": "conf"}).json()["items"]] == ["Past Conf"]
    assert [c["name"] for c in api.get(C, params={"timing": "upcoming", "project_id": str(project.id)}).json()["items"]] == ["Later Conf"]
    window = api.get(C, params={"deadline_from": _when(1), "deadline_to": _when(10), "search": "conf"}).json()
    assert [c["name"] for c in window["items"]] == ["Soon Conf"]
    past = api.get(C, params={"timing": "overdue", "search": "past"}).json()["items"][0]
    assert past["is_overdue"] is True and past["seconds_remaining"] < 0


def test_archive_and_remove_association(login, student, professor, make_user, make_project):
    member = make_user("Student")
    project = make_project(student, members=[(professor, "supervisor"), (member, "member")])
    conference = login(student).post(C, json=_conf(project_id=str(project.id))).json()

    # Another member did not add the link and is not a supervisor.
    assert login(member).post(f"{C}/{conference['id']}/projects/{project.id}/archive").status_code == 403
    assert login(student).post(f"{C}/{conference['id']}/projects/{project.id}/archive").status_code == 200
    active = login(student).get(C, params={"project_id": str(project.id)}).json()
    assert active["total"] == 0
    archived = login(student).get(C, params={"project_id": str(project.id), "include_archived_links": True}).json()
    assert archived["total"] == 1
    assert login(professor).delete(f"{C}/{conference['id']}/projects/{project.id}").status_code == 200
    # The conference record itself remains.
    assert login(student).get(f"{C}/{conference['id']}").status_code == 200


def test_edit_and_delete_permissions(login, student, professor, admin, make_user, make_project):
    project = make_project(student)
    conference = login(student).post(C, json=_conf(project_id=str(project.id))).json()
    other = make_user("Student")
    assert login(other).patch(f"{C}/{conference['id']}", json={"location": "Paris"}).status_code == 403
    assert login(professor).patch(f"{C}/{conference['id']}", json={"location": "Paris"}).json()["location"] == "Paris"
    new_deadline = _when(45)
    updated = login(student).patch(f"{C}/{conference['id']}", json={"submission_deadline": new_deadline}).json()
    assert updated["submission_deadline"].startswith(new_deadline[:16])
    # Still linked: only administrators can delete it.
    assert login(student).delete(f"{C}/{conference['id']}").status_code == 403
    assert login(admin).delete(f"{C}/{conference['id']}").status_code == 200


def test_guest_sees_only_linked_conferences(login, student, guest, make_project):
    project = make_project(student, members=[(guest, "guest")])
    linked = login(student).post(C, json=_conf(project_id=str(project.id))).json()
    other = login(student).post(C, json=_conf(name="Other Conf")).json()
    api = login(guest)
    ids = {c["id"] for c in api.get(C).json()["items"]}
    assert linked["id"] in ids and other["id"] not in ids
    assert api.post(C, json=_conf(name="Guest Conf")).status_code == 403
