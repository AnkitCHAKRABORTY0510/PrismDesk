from datetime import date, timedelta

from app.core.config import settings

H = "/api/v1/handbook"
TODAY = date.today().isoformat()


def _setup(make_user, make_project):
    professor = make_user("Professor")
    student = make_user("Student")
    other_student = make_user("Student")
    other_professor = make_user("Professor")
    project = make_project(student, members=[(professor, "supervisor")])
    make_project(other_student, members=[(other_professor, "supervisor")], title="Other study")
    return professor, student, other_student, other_professor, project


def test_supervisor_reads_shared_note_but_never_private_summary(login, make_user, make_project):
    professor, student, other_student, other_professor, _ = _setup(make_user, make_project)
    student_api = login(student)
    student_api.post(f"{H}/summaries", json={"entry_date": TODAY, "summary": "PRIVATE: I am behind schedule"})
    note = student_api.post(f"{H}/shared-notes", json={"entry_date": TODAY, "body": "  Finished the ablation.  "})
    assert note.status_code == 201, note.text
    note = note.json()
    assert note["body"] == "Finished the ablation." and note["can_edit"] is True

    prof_api = login(professor)
    listed = prof_api.get(f"{H}/shared-notes", params={"date_from": TODAY, "date_to": TODAY}).json()
    assert [n["id"] for n in listed["items"]] == [note["id"]]
    assert listed["items"][0]["can_comment"] is True and listed["items"][0]["can_edit"] is False
    # The private journal stays private.
    assert prof_api.get(f"{H}/summaries").json()["items"] == []
    assert "PRIVATE" not in prof_api.get(f"{H}/shared-notes/{note['id']}").text

    # A professor who does not supervise the student sees nothing.
    other_api = login(other_professor)
    assert other_api.get(f"{H}/shared-notes").json()["items"] == []
    assert other_api.get(f"{H}/shared-notes/{note['id']}").status_code == 404
    assert other_api.get(f"{H}/shared-notes/{note['id']}/versions").status_code == 404
    # Another student cannot read it either.
    assert login(other_student).get(f"{H}/shared-notes/{note['id']}").status_code == 404


def test_shared_note_rules_and_versions(login, make_user, make_project):
    professor, student, *_ = _setup(make_user, make_project)
    api = login(student)
    future = (date.today() + timedelta(days=5)).isoformat()
    assert api.post(f"{H}/shared-notes", json={"entry_date": future, "body": "x"}).status_code == 400
    assert api.post(f"{H}/shared-notes", json={"entry_date": TODAY, "body": "   "}).status_code == 422
    note = api.post(f"{H}/shared-notes", json={"entry_date": TODAY, "body": "v1"}).json()
    assert api.post(f"{H}/shared-notes", json={"entry_date": TODAY, "body": "again"}).status_code == 409
    assert login(professor).post(f"{H}/shared-notes", json={"entry_date": TODAY, "body": "x"}).status_code == 403

    assert api.patch(f"{H}/shared-notes/{note['id']}", json={"body": "v2"}).json()["version"] == 2
    assert login(professor).patch(f"{H}/shared-notes/{note['id']}", json={"body": "edit"}).status_code == 403
    versions = login(professor).get(f"{H}/shared-notes/{note['id']}/versions").json()
    assert [(v["version"], v["snapshot"]["body"]) for v in versions] == [(2, "v2"), (1, "v1")]


def test_shared_note_comment_threads(login, make_user, make_project):
    professor, student, other_student, other_professor, _ = _setup(make_user, make_project)
    note = login(student).post(f"{H}/shared-notes", json={"entry_date": TODAY, "body": "Stuck on loss"}).json()

    # The student cannot start a thread; the supervisor can.
    assert login(student).post(f"{H}/shared-notes/{note['id']}/comments", json={"body": "hi"}).status_code == 403
    commented = login(professor).post(f"{H}/shared-notes/{note['id']}/comments", json={"body": "Try a lower LR"})
    assert commented.status_code == 201
    comment_id = commented.json()["comments"][0]["id"]

    reply = login(student).post(f"{H}/shared-notes/{note['id']}/comments", json={"body": "Works now", "parent_id": comment_id})
    assert reply.json()["comments"][0]["replies"][0]["body"] == "Works now"
    assert reply.json()["comment_count"] == 2
    assert login(other_professor).post(f"{H}/shared-notes/{note['id']}/comments", json={"body": "x"}).status_code == 404


def test_archived_project_supervisor_reads_but_cannot_comment(login, make_user, make_project):
    professor = make_user("Professor")
    student = make_user("Student")
    make_project(student, members=[(professor, "supervisor")], status="archived")
    note = login(student).post(f"{H}/shared-notes", json={"entry_date": TODAY, "body": "Old work"}).json()
    prof_api = login(professor)
    assert prof_api.get(f"{H}/shared-notes/{note['id']}").json()["can_comment"] is False
    assert prof_api.post(f"{H}/shared-notes/{note['id']}/comments", json={"body": "x"}).status_code == 403


def test_guests_have_no_shared_notes(login, make_user):
    assert login(make_user("Guest")).get(f"{H}/shared-notes").status_code == 403


def test_unexpected_errors_are_json_with_cors_headers(login, make_user, monkeypatch):
    from app.services import handbook_planner_service

    def boom(*args, **kwargs):
        raise RuntimeError("relation does not exist")

    monkeypatch.setattr(handbook_planner_service, "planner_range", boom)
    origin = settings.cors_origin_list[0]
    response = login(make_user("Student")).get(
        f"{H}/planner", params={"date_from": TODAY, "date_to": TODAY}, headers={"Origin": origin}
    )
    assert response.status_code == 500
    assert response.json()["detail"].startswith("The server hit an unexpected error")
    assert response.headers["access-control-allow-origin"] == origin
