"""Test fixtures.

Tests run against the real PostgreSQL server but inside a dedicated
``prism_test`` schema, so application data in ``public`` is never read
or written. The schema is migrated with Alembic (which also verifies the
migrations), and every test runs inside a transaction that is rolled
back afterwards.
"""

import uuid
from datetime import datetime, timezone

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.core.security import hash_password
from app.database.session import DATABASE_URL, get_db
from app.models.role import Role
from app.models.user import User
from main import app

TEST_SCHEMA = "prism_test"
TEST_PASSWORD = "Correct-Horse-42!"

test_engine = create_engine(
    DATABASE_URL,
    connect_args={"options": f"-csearch_path={TEST_SCHEMA}"},
)


@pytest.fixture(scope="session", autouse=True)
def migrated_schema():
    with test_engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {TEST_SCHEMA}"))

    config = Config("alembic.ini")
    with test_engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")

    yield


@pytest.fixture()
def connection(migrated_schema):
    conn = test_engine.connect()
    outer = conn.begin()
    try:
        yield conn
    finally:
        outer.rollback()
        conn.close()


@pytest.fixture()
def db(connection):
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def override_db(connection):
    def _get_db():
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_db
    limiter.reset()
    yield
    app.dependency_overrides.clear()
    limiter.reset()


_PASSWORD_HASH = hash_password(TEST_PASSWORD)


@pytest.fixture()
def make_user(db):
    def _make(
        *roles: str,
        status: str = "approved",
        username: str | None = None,
    ) -> User:
        name = username or f"user_{uuid.uuid4().hex[:10]}"
        user = User(
            username=name,
            email=f"{name}@prismlab.org",
            full_name=name.replace("_", " ").title(),
            password_hash=_PASSWORD_HASH,
            account_status=status,
            approved_at=datetime.now(timezone.utc) if status == "approved" else None,
        )
        if roles:
            user.roles = list(
                db.scalars(select(Role).where(Role.name.in_(roles))).all()
            )
        db.add(user)
        db.commit()
        return user

    return _make


class ApiClient(TestClient):
    """TestClient that remembers the CSRF token after logging in."""

    csrf_token: str | None = None

    def request(self, method, url, **kwargs):
        if self.csrf_token and method.upper() not in {"GET", "HEAD", "OPTIONS"}:
            headers = dict(kwargs.pop("headers", None) or {})
            headers.setdefault("X-CSRF-Token", self.csrf_token)
            kwargs["headers"] = headers
        return super().request(method, url, **kwargs)


@pytest.fixture()
def client():
    return ApiClient(app)


@pytest.fixture()
def login():
    def _login(user: User) -> ApiClient:
        api = ApiClient(app)
        response = api.post(
            "/api/v1/auth/login",
            json={"identifier": user.username, "password": TEST_PASSWORD},
        )
        assert response.status_code == 200, response.text
        api.csrf_token = response.json()["csrf_token"]
        return api

    return _login


@pytest.fixture()
def admin(make_user):
    return make_user("Administrator")


@pytest.fixture()
def professor(make_user):
    return make_user("Professor")


@pytest.fixture()
def student(make_user):
    return make_user("Student")


@pytest.fixture()
def guest(make_user):
    return make_user("Guest")
