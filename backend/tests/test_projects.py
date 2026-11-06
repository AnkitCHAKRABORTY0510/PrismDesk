from datetime import timedelta

from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.project import Project, ProjectMember

P = "/api/v1/projects"


def test_student_creates_project_and_becomes_owner_member(login, student, db):
    api = login(student)
    response = api.post(P, json={"title": "Hyperspectral denoising", "description": "d", "objectives": "o"})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["owner"]["id"] == str(student.id)
    assert body["my_role"] == "owner"
    assert body["permissions"]["can_edit"] is True
    assert body["permissions"]["can_manage_members"] is False
    assert body["permissions"]["can_archive"] is False
    assert body["permissions"]["can_request_archive"] is True

    membership = db.scalar(select(ProjectMember).where(ProjectMember.project_id == body["id"]))
    assert membership.user_id == student.id and membership.membership_role == "owner"
    assert db.scalar(select(AuditLog).where(AuditLog.action == "project.created", AuditLog.entity_id == body["id"]))


def test_guest_cannot_create_project(login, guest):
    assert login(guest).post(P, json={"title": "Not allowed"}).status_code == 403


def test_create_validation(login, student):
    assert login(student).post(P, json={"title": "  "}).status_code == 422


def test_student_owner_cannot_manage_members(login, student, make_user, make_project):
    project = make_project(student)
    other = make_user("Student")
    response = login(student).post(f"{P}/{project.id}/members", json={"user_id": str(other.id), "membership_role": "member"})
    assert response.status_code == 403


def test_non_member_cannot_see_project(login, student, make_user, make_project):
    project = make_project(student)
    outsider = make_user("Student")
    professor = make_user("Professor")
    assert login(outsider).get(f"{P}/{project.id}").status_code == 404
    assert login(professor).get(f"{P}/{project.id}").status_code == 404
    listing = login(outsider).get(P).json()
    assert all(item["id"] != str(project.id) for item in listing["items"])


def test_admin_adds_supervisor_who_manages_members(login, admin, student, professor, make_user, make_project):
    project = make_project(student)
    admin_api = login(admin)
    response = admin_api.post(f"{P}/{project.id}/members", json={"user_id": str(professor.id), "membership_role": "supervisor"})
    assert response.status_code == 201

    prof_api = login(professor)
    detail = prof_api.get(f"{P}/{project.id}").json()
    assert detail["permissions"]["can_manage_members"] is True
    assert [s["id"] for s in detail["supervisors"]] == [str(professor.id)]

    new_student = make_user("Student")
    response = prof_api.post(f"{P}/{project.id}/members", json={"user_id": str(new_student.id), "membership_role": "member"})
    assert response.status_code == 201
    assert prof_api.post(f"{P}/{project.id}/members", json={"user_id": str(new_student.id), "membership_role": "member"}).status_code == 409

    # Members see the project; removal hides it again but keeps history.
    assert login(new_student).get(f"{P}/{project.id}").status_code == 200
    assert prof_api.delete(f"{P}/{project.id}/members/{new_student.id}").status_code == 200
    assert login(new_student).get(f"{P}/{project.id}").status_code == 404
    history = prof_api.get(f"{P}/{project.id}/members", params={"include_removed": True}).json()
    assert any(m["user"]["id"] == str(new_student.id) and m["membership_status"] == "removed" for m in history)


def test_member_role_validation(login, admin, student, make_user, make_project):
    project = make_project(student)
    api = login(admin)
    other_student = make_user("Student")
    guest = make_user("Guest")
    assert api.post(f"{P}/{project.id}/members", json={"user_id": str(other_student.id), "membership_role": "supervisor"}).status_code == 400
    assert api.post(f"{P}/{project.id}/members", json={"user_id": str(guest.id), "membership_role": "member"}).status_code == 400
    assert api.post(f"{P}/{project.id}/members", json={"user_id": str(guest.id), "membership_role": "guest"}).status_code == 201


def test_guest_member_is_read_only(login, admin, student, guest, make_project):
    project = make_project(student, members=[(guest, "guest")])
    api = login(guest)
    detail = api.get(f"{P}/{project.id}").json()
    assert detail["permissions"]["can_contribute"] is False
    assert detail["permissions"]["can_edit"] is False
    assert api.patch(f"{P}/{project.id}", json={"title": "Changed"}).status_code == 403


def test_owner_cannot_be_removed(login, admin, student, make_project):
    project = make_project(student)
    assert login(admin).delete(f"{P}/{project.id}/members/{student.id}").status_code == 409


def test_archive_flow(login, admin, student, professor, make_project):
    project = make_project(student, members=[(professor, "supervisor")])
    student_api = login(student)
    prof_api = login(professor)

    assert student_api.post(f"{P}/{project.id}/archive").status_code == 403
    response = student_api.post(f"{P}/{project.id}/archive-request", json={"reason": "Finished"})
    assert response.status_code == 200
    assert response.json()["archive_requested_at"]

    response = prof_api.post(f"{P}/{project.id}/archive")
    assert response.status_code == 200 and response.json()["status"] == "archived"

    # Archived projects are read-only for ordinary activity.
    assert student_api.patch(f"{P}/{project.id}", json={"title": "Edited after archive"}).status_code == 403
    assert prof_api.post(f"{P}/{project.id}/unarchive").json()["status"] == "active"


def test_soft_delete_restore_and_purge(login, admin, student, professor, make_project, db):
    project = make_project(student, members=[(professor, "supervisor")])
    assert login(student).delete(f"{P}/{project.id}").status_code == 403
    assert login(professor).delete(f"{P}/{project.id}").json()["status"] == "deleted"

    # Hidden from members, visible to admins under the deleted filter.
    assert login(student).get(f"{P}/{project.id}").status_code == 404
    admin_api = login(admin)
    deleted = admin_api.get(P, params={"status": "deleted"}).json()
    assert any(item["id"] == str(project.id) for item in deleted["items"])
    assert login(student).get(P, params={"status": "deleted"}).status_code == 403

    # Only admins restore; purge is blocked during the retention window.
    assert login(professor).post(f"{P}/{project.id}/restore").status_code == 404
    assert admin_api.delete(f"{P}/{project.id}/permanent").status_code == 409
    assert admin_api.post(f"{P}/{project.id}/restore").json()["status"] == "active"

    admin_api.delete(f"{P}/{project.id}")
    db.expire_all()
    stored = db.get(Project, project.id)
    stored.deleted_at = stored.deleted_at - timedelta(days=91)
    db.commit()
    assert login(professor).delete(f"{P}/{project.id}/permanent").status_code == 404
    project_id = stored.id
    assert admin_api.delete(f"{P}/{project_id}/permanent").status_code == 200
    db.expire_all()
    assert db.get(Project, project_id) is None


def test_transfer_ownership_admin_only(login, admin, student, make_user, make_project):
    project = make_project(student)
    new_owner = make_user("Student")
    assert login(student).post(f"{P}/{project.id}/transfer-ownership", json={"new_owner_id": str(new_owner.id)}).status_code == 403
    response = login(admin).post(f"{P}/{project.id}/transfer-ownership", json={"new_owner_id": str(new_owner.id)})
    assert response.status_code == 200
    assert response.json()["owner"]["id"] == str(new_owner.id)
    members = login(admin).get(f"{P}/{project.id}/members").json()
    roles = {m["user"]["id"]: m["membership_role"] for m in members}
    assert roles[str(student.id)] == "member" and roles[str(new_owner.id)] == "owner"


def test_user_project_listing(login, admin, student, make_project):
    make_project(student, title="Alpha")
    make_project(student, title="Beta")
    mine = login(student).get(P, params={"mine": True}).json()
    assert mine["total"] == 2
    by_user = login(admin).get(P, params={"user_id": str(student.id)}).json()
    assert by_user["total"] == 2
    assert login(student).get(P, params={"user_id": str(admin.id)}).status_code == 403
    assert login(student).get(P, params={"search": "alp"}).json()["total"] == 1
