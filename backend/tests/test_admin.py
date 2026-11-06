from sqlalchemy import select, text

import pytest
from sqlalchemy.exc import DBAPIError

from app.models.audit_log import AuditLog
from app.models.user import User
from tests.conftest import TEST_PASSWORD

ADMIN = "/api/v1/admin"


def _audit_actions(db, user_id):
    return set(db.scalars(select(AuditLog.action).where(AuditLog.entity_id == str(user_id))).all())


def test_admin_routes_reject_non_admins(login, student, professor, guest, client):
    assert client.get(f"{ADMIN}/users").status_code == 401
    for user in (student, professor, guest):
        assert login(user).get(f"{ADMIN}/users").status_code == 403
        assert login(user).get("/api/v1/audit/logs").status_code == 403


def test_approve_records_metadata_and_audit(login, admin, make_user, db):
    pending = make_user(status="pending")
    api = login(admin)
    response = api.post(f"{ADMIN}/users/{pending.id}/approve", json={"role_name": "Professor"})
    assert response.status_code == 200
    assert response.json()["roles"] == ["Professor"]

    db.expire_all()
    user = db.get(User, pending.id)
    assert user.account_status == "approved"
    assert user.approved_by == admin.id
    assert "user.approved" in _audit_actions(db, pending.id)


def test_approval_cannot_grant_administrator(login, admin, make_user):
    pending = make_user(status="pending")
    response = login(admin).post(f"{ADMIN}/users/{pending.id}/approve", json={"role_name": "Administrator"})
    assert response.status_code == 422


def test_approve_twice_conflicts(login, admin, make_user):
    pending = make_user(status="pending")
    api = login(admin)
    assert api.post(f"{ADMIN}/users/{pending.id}/approve", json={"role_name": "Student"}).status_code == 200
    assert api.post(f"{ADMIN}/users/{pending.id}/approve", json={"role_name": "Student"}).status_code == 409


def test_reject_records_rejected_by(login, admin, make_user, db):
    pending = make_user(status="pending")
    response = login(admin).post(f"{ADMIN}/users/{pending.id}/reject")
    assert response.status_code == 200
    db.expire_all()
    user = db.get(User, pending.id)
    assert user.account_status == "rejected"
    assert user.rejected_by == admin.id
    assert user.rejected_at is not None
    assert "user.rejected" in _audit_actions(db, pending.id)


def test_suspend_revokes_sessions_and_reactivate_requires_login(login, admin, student, client):
    student_api = login(student)
    assert student_api.get("/api/v1/auth/me").status_code == 200

    admin_api = login(admin)
    assert admin_api.patch(f"{ADMIN}/users/{student.id}/suspend").status_code == 200
    assert student_api.get("/api/v1/auth/me").status_code == 401

    assert admin_api.patch(f"{ADMIN}/users/{student.id}/reactivate").status_code == 200
    # The old session stays dead; a fresh login works.
    assert student_api.get("/api/v1/auth/me").status_code == 401
    response = client.post("/api/v1/auth/login", json={"identifier": student.username, "password": TEST_PASSWORD})
    assert response.status_code == 200


def test_admin_cannot_suspend_self(login, admin):
    assert login(admin).patch(f"{ADMIN}/users/{admin.id}/suspend").status_code == 400


def test_role_assignment_and_removal(login, admin, student, db):
    api = login(admin)
    response = api.post(f"{ADMIN}/users/{student.id}/roles", json={"role_name": "Professor"})
    assert response.status_code == 200
    assert response.json()["roles"] == ["Professor", "Student"]
    assert api.post(f"{ADMIN}/users/{student.id}/roles", json={"role_name": "Professor"}).status_code == 409

    response = api.delete(f"{ADMIN}/users/{student.id}/roles/Professor")
    assert response.status_code == 200
    assert response.json()["roles"] == ["Student"]

    # The last remaining role cannot be removed.
    assert api.delete(f"{ADMIN}/users/{student.id}/roles/Student").status_code == 409
    actions = _audit_actions(db, student.id)
    assert {"user.role_assigned", "user.role_removed"} <= actions


def test_admin_cannot_remove_own_admin_role(login, make_user):
    admin = make_user("Administrator", "Professor")
    response = login(admin).delete(f"{ADMIN}/users/{admin.id}/roles/Administrator")
    assert response.status_code == 403


def test_last_admin_protection(make_user, db):
    from app.core.errors import ConflictError
    from app.services import admin_service

    # The isolated schema holds only the administrators made here.
    only_admin = make_user("Administrator", "Professor")
    acting = make_user("Professor")
    with pytest.raises(ConflictError):
        admin_service.remove_role(db, only_admin.id, "Administrator", acting)
    with pytest.raises(ConflictError):
        admin_service.suspend_user(db, only_admin.id, acting)

    make_user("Administrator")
    admin_service.remove_role(db, only_admin.id, "Administrator", acting)


def test_non_admin_cannot_escalate(login, student):
    response = login(student).post(f"{ADMIN}/users/{student.id}/roles", json={"role_name": "Administrator"})
    assert response.status_code == 403


def test_user_list_pagination_and_filters(login, admin, make_user):
    for index in range(3):
        make_user("Student", username=f"paging_student_{index}")
    api = login(admin)
    response = api.get(f"{ADMIN}/users", params={"search": "paging_student", "page_size": 2})
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert api.get(f"{ADMIN}/users", params={"account_status": "bogus"}).status_code == 422
    filtered = api.get(f"{ADMIN}/users", params={"role_name": "Administrator"}).json()
    assert all("Administrator" in item["roles"] for item in filtered["items"])


def test_audit_log_is_append_only(login, admin, make_user, db):
    pending = make_user(status="pending")
    login(admin).post(f"{ADMIN}/users/{pending.id}/reject")
    response = login(admin).get("/api/v1/audit/logs", params={"action": "user.rejected"})
    assert response.status_code == 200
    assert response.json()["total"] >= 1

    with pytest.raises(DBAPIError):
        with db.begin_nested():
            db.execute(text("DELETE FROM audit_logs"))
