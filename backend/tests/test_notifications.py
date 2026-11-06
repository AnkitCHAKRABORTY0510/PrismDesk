from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.notification import DiscordAccount, Notification, NotificationDeliveryAttempt
from app.services import discord_client, notification_service
from app.services.discord_client import DeliveryResult
from app.workers import notification_worker

N = "/api/v1/notifications"


def link(db, user, discord_id="123456789"):
    db.add(DiscordAccount(user_id=user.id, discord_user_id=discord_id, discord_username="lab_user"))
    db.commit()


class FakeSender:
    def __init__(self, results):
        self.results = list(results)
        self.messages = []

    def open_dm_channel(self, discord_user_id):
        return DeliveryResult(True, 200, channel_id="dm-1")

    def send_message(self, channel_id, content):
        self.messages.append((channel_id, content))
        return self.results.pop(0)


@pytest.fixture()
def bot_token(monkeypatch):
    monkeypatch.setattr(settings, "DISCORD_BOT_TOKEN", "test-token")


def _queue(db, user, key="k1", category="tasks"):
    return notification_service.enqueue_notification(
        db, recipient_id=user.id, category=category, event_type="test", title="Hello", body="World", dedupe_key=key
    )


def test_enqueue_requires_link_and_respects_preferences(db, login, student):
    assert _queue(db, student) is False  # no linked Discord account
    link(db, student)
    assert _queue(db, student) is True
    assert _queue(db, student) is False  # duplicate key ignored
    login(student).put(f"{N}/preferences", json={"preferences": [{"category": "tasks", "enabled": False}]})
    assert _queue(db, student, key="k2") is False
    assert _queue(db, student, key="k3", category="projects") is True


def test_task_assignment_queues_notification(db, login, make_user, make_project):
    professor = make_user("Professor")
    student = make_user("Student")
    project = make_project(student, members=[(professor, "supervisor")])
    link(db, student)
    response = login(professor).post(
        "/api/v1/tasks",
        json={"task_type": "official", "title": "Survey", "project_id": str(project.id), "assignee_ids": [str(student.id)]},
    )
    assert response.status_code == 201
    queued = db.scalars(select(Notification).where(Notification.recipient_id == student.id)).all()
    assert [n.event_type for n in queued] == ["task.assigned"]


def test_notification_failure_never_breaks_business_operation(db, login, make_user, make_project, monkeypatch):
    professor = make_user("Professor")
    student = make_user("Student")
    project = make_project(student, members=[(professor, "supervisor")])
    link(db, student)

    def explode(*args, **kwargs):
        raise RuntimeError("discord down")

    monkeypatch.setattr(notification_service, "linked_account", explode)
    response = login(professor).post(
        "/api/v1/tasks",
        json={"task_type": "official", "title": "Survey", "project_id": str(project.id), "assignee_ids": [str(student.id)]},
    )
    assert response.status_code == 201


def test_worker_sends_and_records_attempt(db, student, bot_token):
    link(db, student)
    _queue(db, student)
    sender = FakeSender([DeliveryResult(True, 200)])
    summary = notification_worker.run_once(db, sender)
    assert summary == {"sent": 1}
    notification = db.scalar(select(Notification).where(Notification.recipient_id == student.id))
    assert notification.status == "sent" and notification.sent_at
    attempts = db.scalars(select(NotificationDeliveryAttempt)).all()
    assert len(attempts) == 1 and attempts[0].success
    assert sender.messages[0][0] == "dm-1"


def test_worker_retries_with_backoff_then_fails(db, student, bot_token, monkeypatch):
    monkeypatch.setattr(settings, "NOTIFICATION_MAX_ATTEMPTS", 2)
    link(db, student)
    _queue(db, student)
    now = datetime.now(timezone.utc)

    sender = FakeSender([DeliveryResult(False, 503, "unavailable"), DeliveryResult(False, 503, "unavailable")])
    notification_worker.run_once(db, sender, now)
    notification = db.scalar(select(Notification).where(Notification.recipient_id == student.id))
    assert notification.status == "retry_scheduled"
    assert notification.next_attempt_at == now + timedelta(seconds=settings.NOTIFICATION_RETRY_BASE_SECONDS)

    # Not due yet: nothing happens.
    assert notification_worker.run_once(db, sender, now + timedelta(seconds=1)) == {}
    notification_worker.run_once(db, sender, now + timedelta(hours=1))
    db.refresh(notification)
    assert notification.status == "failed" and notification.attempt_count == 2


def test_permanent_errors_fail_immediately(db, student, bot_token):
    link(db, student)
    _queue(db, student)
    notification_worker.run_once(db, FakeSender([DeliveryResult(False, 403, "blocked", retryable=False)]))
    assert db.scalar(select(Notification.status)) == "failed"


def test_missing_bot_token_is_retried(db, student, monkeypatch):
    monkeypatch.setattr(settings, "DISCORD_BOT_TOKEN", "")
    link(db, student)
    _queue(db, student)
    notification_worker.run_once(db, FakeSender([]))
    assert db.scalar(select(Notification.status)) == "retry_scheduled"


def test_reminders_are_deduplicated(db, login, make_user, make_project):
    professor = make_user("Professor")
    student = make_user("Student")
    project = make_project(student, members=[(professor, "supervisor")])
    link(db, student)
    due = (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat()
    login(professor).post(
        "/api/v1/tasks",
        json={"task_type": "official", "title": "Due soon", "project_id": str(project.id), "due_at": due, "assignee_ids": [str(student.id)]},
    )
    deadline = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    login(student).post(
        "/api/v1/conferences",
        json={"name": "ICCV", "submission_deadline": deadline, "project_id": str(project.id)},
    )

    first = notification_worker.schedule_reminders(db)
    assert first == 2
    assert notification_worker.schedule_reminders(db) == 0
    events = set(db.scalars(select(Notification.event_type).where(Notification.recipient_id == student.id)).all())
    assert {"task.due_soon", "conference.deadline_approaching"} <= events


def test_preferences_api(login, student):
    api = login(student)
    defaults = api.get(f"{N}/preferences").json()
    assert all(item["enabled"] for item in defaults) and len(defaults) == 5
    updated = api.put(f"{N}/preferences", json={"preferences": [{"category": "handbook", "enabled": False}]}).json()
    assert {i["category"]: i["enabled"] for i in updated}["handbook"] is False
    assert api.put(f"{N}/preferences", json={"preferences": [{"category": "chat", "enabled": False}]}).status_code == 422


def test_discord_oauth_link_flow(db, login, student, make_user, monkeypatch):
    monkeypatch.setattr(settings, "DISCORD_CLIENT_ID", "client")
    monkeypatch.setattr(settings, "DISCORD_CLIENT_SECRET", "secret")
    monkeypatch.setattr(settings, "DISCORD_REDIRECT_URI", "http://testserver/api/v1/notifications/discord/callback")
    monkeypatch.setattr(discord_client, "oauth_fetch_identity", lambda code: {"id": "998877", "username": "ankit"})

    api = login(student)
    assert api.get(f"{N}/discord").json()["linked"] is False
    url = api.post(f"{N}/discord/link").json()["authorize_url"]
    state = url.split("state=")[1].split("&")[0]
    assert "client_secret" not in url

    # Another user cannot complete someone else's state.
    intruder = login(make_user("Student"))
    response = intruder.get(f"{N}/discord/callback", params={"code": "c", "state": state}, follow_redirects=False)
    assert response.headers["location"].endswith("discord=error")

    response = api.get(f"{N}/discord/callback", params={"code": "c", "state": state}, follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"].endswith("discord=linked")
    status = api.get(f"{N}/discord").json()
    assert status["linked"] is True and status["discord_username"] == "ankit"

    # States are single-use.
    response = api.get(f"{N}/discord/callback", params={"code": "c", "state": state}, follow_redirects=False)
    assert response.headers["location"].endswith("discord=error")

    assert api.delete(f"{N}/discord").status_code == 200
    assert api.get(f"{N}/discord").json()["linked"] is False


def test_link_unavailable_without_configuration(login, student, monkeypatch):
    monkeypatch.setattr(settings, "DISCORD_CLIENT_ID", "")
    assert login(student).post(f"{N}/discord/link").status_code == 400


def test_announcements_admin_only(db, login, admin, student, monkeypatch):
    monkeypatch.setattr(settings, "DISCORD_ANNOUNCEMENT_CHANNEL_ID", "555")
    link(db, student)
    assert login(student).post(f"{N}/announcements", json={"title": "x", "body": "y"}).status_code == 403
    response = login(admin).post(
        f"{N}/announcements", json={"title": "Lab closed", "body": "Friday", "direct_message_all": True}
    )
    assert response.status_code == 200
    assert response.json()["queued"] >= 2  # channel + linked student
    queue = login(admin).get(f"{N}/queue").json()
    assert queue["total"] >= 2
    assert login(student).get(f"{N}/queue").status_code == 403
    assert login(student).get(f"{N}/history").json()["total"] == 1
