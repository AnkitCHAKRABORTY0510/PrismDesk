from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import settings
from app.core.session_security import hash_session_token
from app.models.user import User
from app.models.user_session import UserSession
from tests.conftest import TEST_PASSWORD

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
LOGOUT = "/api/v1/auth/logout"


def _register(client, username="new_student", **overrides):
    payload = {
        "username": username,
        "email": f"{username}@prismlab.org",
        "full_name": "New Student",
        "password": TEST_PASSWORD,
    }
    payload.update(overrides)
    return client.post(REGISTER, json=payload)


def test_register_creates_pending_user_without_roles(client, db):
    response = _register(client)
    assert response.status_code == 201
    assert response.json()["account_status"] == "pending"

    user = db.scalar(select(User).where(User.username == "new_student"))
    assert user.roles == []
    assert user.password_hash != TEST_PASSWORD
    assert user.password_hash.startswith("$argon2id$")


def test_register_ignores_role_fields(client, db):
    response = _register(client, username="sneaky", roles=["Administrator"], role_name="Administrator")
    assert response.status_code == 201
    user = db.scalar(select(User).where(User.username == "sneaky"))
    assert user.roles == []
    assert user.account_status == "pending"


def test_register_duplicate_username_and_email(client):
    assert _register(client, username="dup_user").status_code == 201
    assert _register(client, username="DUP_USER", email="other@prismlab.org").status_code == 409
    assert _register(client, username="another", email="dup_user@prismlab.org").status_code == 409


def test_register_validation(client):
    assert _register(client, password="short").status_code == 422
    assert _register(client, username="bad name!").status_code == 422
    assert _register(client, email="not-an-email").status_code == 422


def test_pending_rejected_suspended_cannot_login(client, make_user):
    for status in ("pending", "rejected", "suspended"):
        user = make_user("Student", status=status)
        response = client.post(LOGIN, json={"identifier": user.username, "password": TEST_PASSWORD})
        assert response.status_code == 403, status


def test_login_with_username_or_email_sets_httponly_cookie(client, student):
    response = client.post(LOGIN, json={"identifier": student.email.upper(), "password": TEST_PASSWORD})
    assert response.status_code == 200
    body = response.json()
    assert body["roles"] == ["Student"]
    assert "handbook.write" in body["capabilities"]
    assert body["csrf_token"]

    cookie_header = response.headers["set-cookie"]
    assert settings.SESSION_COOKIE_NAME in cookie_header
    assert "HttpOnly" in cookie_header
    assert "samesite=lax" in cookie_header.lower()


def test_login_wrong_password(client, student):
    response = client.post(LOGIN, json={"identifier": student.username, "password": "wrong-password-123"})
    assert response.status_code == 401
    response = client.post(LOGIN, json={"identifier": "nobody_here", "password": "wrong-password-123"})
    assert response.status_code == 401


def test_me_requires_authentication(client):
    assert client.get(ME).status_code == 401


def test_me_and_logout(login, student):
    api = login(student)
    assert api.get(ME).json()["username"] == student.username

    assert api.post(LOGOUT).status_code == 200
    assert api.get(ME).status_code == 401


def test_mutation_without_csrf_token_is_rejected(login, admin, make_user):
    pending = make_user(status="pending")
    api = login(admin)
    token = api.csrf_token
    api.csrf_token = None

    response = api.post(f"/api/v1/admin/users/{pending.id}/approve", json={"role_name": "Student"})
    assert response.status_code == 403
    assert "CSRF" in response.json()["detail"]

    response = api.post(
        f"/api/v1/admin/users/{pending.id}/approve",
        json={"role_name": "Student"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 200


def test_session_inactivity_timeout(login, student, db):
    api = login(student)
    session = db.scalar(select(UserSession).where(UserSession.user_id == student.id))
    session.last_activity_at = datetime.now(timezone.utc) - timedelta(
        minutes=settings.SESSION_INACTIVITY_MINUTES + 1
    )
    db.commit()
    assert api.get(ME).status_code == 401


def test_session_absolute_expiry(login, student, db):
    api = login(student)
    session = db.scalar(select(UserSession).where(UserSession.user_id == student.id))
    session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    assert api.get(ME).status_code == 401


def test_session_token_stored_hashed(login, student, db):
    api = login(student)
    token = api.cookies.get(settings.SESSION_COOKIE_NAME)
    session = db.scalar(select(UserSession).where(UserSession.user_id == student.id))
    assert session.token_hash == hash_session_token(token)
    assert session.token_hash != token


def test_login_rate_limit(client, student):
    statuses = [
        client.post(LOGIN, json={"identifier": student.username, "password": "wrong-password-123"}).status_code
        for _ in range(settings.LOGIN_RATE_LIMIT + 1)
    ]
    assert statuses[-1] == 429
