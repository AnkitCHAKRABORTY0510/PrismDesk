"""Scheduled outbox delivery, handbook reminder DMs and the test-message endpoint.

Discord is never contacted: the worker gets either a fake sender or the real
``DiscordSender`` wired to an ``httpx.MockTransport``.
"""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.handbook import HandbookReminder
from app.models.notification import Notification
from app.services import handbook_reminder_dispatch, notification_service
from app.services.discord_client import DeliveryResult, DiscordSender
from app.workers import notification_worker
from tests.test_notifications import FakeSender, link

N = "/api/v1/notifications"
NOW = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)


@pytest.fixture()
def bot_token(monkeypatch):
    monkeypatch.setattr(settings, "DISCORD_BOT_TOKEN", "test-token")


def _reminder(db, owner, remind_at, note="Submit the camera-ready draft"):
    reminder = HandbookReminder(owner_id=owner.id, reminder_date=remind_at.date(), remind_at=remind_at, note=note)
    db.add(reminder)
    db.commit()
    return reminder


def _rows(db, user):
    return db.scalars(select(Notification).where(Notification.recipient_id == user.id)).all()


# --- scheduled outbox -------------------------------------------------------------


def test_deliver_after_holds_message_until_due(db, student, bot_token):
    link(db, student)
    due = NOW + timedelta(hours=2)
    assert notification_service.enqueue_notification(
        db, recipient_id=student.id, category="tasks", event_type="test",
        title="Later", dedupe_key="later", deliver_after=due,
    )
    sender = FakeSender([DeliveryResult(True, 200)])

    assert notification_worker.run_once(db, sender, NOW) == {}
    assert notification_worker.run_once(db, sender, due - timedelta(seconds=1)) == {}
    assert sender.messages == []

    assert notification_worker.run_once(db, sender, due) == {"sent": 1}
    assert len(sender.messages) == 1


def test_enqueue_without_deliver_after_is_immediate(db, student, bot_token):
    link(db, student)
    notification_service.enqueue_notification(
        db, recipient_id=student.id, category="tasks", event_type="test", title="Now", dedupe_key="now"
    )
    assert notification_worker.run_once(db, FakeSender([DeliveryResult(True, 200)])) == {"sent": 1}


def test_naive_deliver_after_is_rejected_without_raising(db, student):
    link(db, student)
    queued = notification_service.enqueue_notification(
        db, recipient_id=student.id, category="tasks", event_type="test", title="x",
        dedupe_key="naive", deliver_after=datetime(2026, 11, 11, 12, 0),
    )
    assert queued is False and _rows(db, student) == []


# --- handbook reminders -------------------------------------------------------------


def test_reminder_is_queued_once_and_sent_at_remind_at(db, student, bot_token):
    link(db, student)
    remind_at = NOW + timedelta(minutes=5)
    _reminder(db, student, remind_at)

    assert handbook_reminder_dispatch.dispatch_due_reminders(db, NOW) == 1
    assert handbook_reminder_dispatch.dispatch_due_reminders(db, NOW + timedelta(minutes=1)) == 0  # idempotent
    [row] = _rows(db, student)
    assert row.event_type == "handbook.reminder" and row.category == "handbook"
    assert row.next_attempt_at == remind_at
    assert "camera-ready" in row.body and f"<t:{int(remind_at.timestamp())}:F>" in row.body

    sender = FakeSender([DeliveryResult(True, 200)])
    assert notification_worker.run_once(db, sender, NOW + timedelta(minutes=4)) == {}
    assert notification_worker.run_once(db, sender, remind_at) == {"sent": 1}


def test_reminder_window_and_eligibility(db, login, make_user):
    linked, unlinked, opted_out = make_user("Student"), make_user("Student"), make_user("Student")
    link(db, linked, "1")
    link(db, opted_out, "2")
    login(opted_out).put(f"{N}/preferences", json={"preferences": [{"category": "handbook", "enabled": False}]})

    _reminder(db, linked, NOW + timedelta(hours=3), "too far ahead")
    _reminder(db, linked, NOW - timedelta(hours=2), "missed long ago")
    dismissed = _reminder(db, linked, NOW + timedelta(minutes=2), "dismissed")
    dismissed.dismissed_at = NOW
    _reminder(db, linked, NOW - timedelta(minutes=20), "missed recently")
    _reminder(db, unlinked, NOW + timedelta(minutes=2))
    _reminder(db, opted_out, NOW + timedelta(minutes=2))
    db.commit()

    assert handbook_reminder_dispatch.dispatch_due_reminders(db, NOW) == 1
    [row] = _rows(db, linked)
    assert row.body.startswith("missed recently")
    assert _rows(db, unlinked) == [] and _rows(db, opted_out) == []


@pytest.mark.parametrize("change", ["dismiss", "delete", "move"])
def test_reminder_changed_after_queueing_is_not_sent(db, student, bot_token, change):
    link(db, student)
    reminder = _reminder(db, student, NOW + timedelta(minutes=5))
    handbook_reminder_dispatch.dispatch_due_reminders(db, NOW)

    if change == "dismiss":
        reminder.dismissed_at = NOW
    elif change == "delete":
        db.delete(reminder)
    else:
        reminder.remind_at = NOW + timedelta(minutes=7)
    db.commit()

    sender = FakeSender([DeliveryResult(True, 200)] * 2)
    notification_worker.run_once(db, sender, NOW + timedelta(minutes=5))
    original = db.scalar(
        select(Notification).where(Notification.recipient_id == student.id).order_by(Notification.created_at)
    )
    assert original.status == "failed" and "Reminder was" in original.last_error
    assert sender.messages == []

    if change == "move":
        # The new time is queued as a fresh notification and delivered.
        assert handbook_reminder_dispatch.dispatch_due_reminders(db, NOW + timedelta(minutes=5)) == 1
        assert notification_worker.run_once(db, sender, NOW + timedelta(minutes=7)) == {"sent": 1}


def test_reminder_dm_through_discord_http_mock(db, student, bot_token):
    """Full path through the real DiscordSender with HTTP mocked."""

    link(db, student, "424242")
    _reminder(db, student, NOW + timedelta(minutes=1), "Lab meeting")
    handbook_reminder_dispatch.dispatch_due_reminders(db, NOW)

    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.headers["Authorization"] == "Bot test-token"
        if request.url.path.endswith("/users/@me/channels"):
            return httpx.Response(200, json={"id": "dm-channel-9"})
        if request.url.path.endswith("/channels/dm-channel-9/messages"):
            return httpx.Response(200, json={"id": "msg-1"})
        return httpx.Response(404)

    sender = DiscordSender(httpx.Client(transport=httpx.MockTransport(handler)))
    assert notification_worker.run_once(db, sender, NOW + timedelta(minutes=1)) == {"sent": 1}
    assert [c.url.path for c in calls] == ["/api/v10/users/@me/channels", "/api/v10/channels/dm-channel-9/messages"]
    payload = calls[1].read().decode()
    assert "Lab meeting" in payload and '"allowed_mentions":{"parse":[]}' in payload.replace(" ", "")


def test_blocked_dm_fails_without_retry(db, student, bot_token):
    """Discord error 50007 (user does not accept DMs from the bot) is permanent."""

    link(db, student)
    _reminder(db, student, NOW + timedelta(minutes=1))
    handbook_reminder_dispatch.dispatch_due_reminders(db, NOW)

    def handler(request):
        if request.url.path.endswith("/users/@me/channels"):
            return httpx.Response(200, json={"id": "dm"})
        return httpx.Response(403, json={"code": 50007, "message": "Cannot send messages to this user"})

    sender = DiscordSender(httpx.Client(transport=httpx.MockTransport(handler)))
    assert notification_worker.run_once(db, sender, NOW + timedelta(minutes=1)) == {"failed": 1}


# --- test-message endpoint --------------------------------------------------------


def test_send_test_message_endpoint(db, login, student, bot_token):
    api = login(student)
    assert api.post(f"{N}/discord/test").status_code == 400  # not linked

    link(db, student)
    response = api.post(f"{N}/discord/test")
    assert response.status_code == 200 and "queued" in response.json()["message"]
    [row] = _rows(db, student)
    assert row.event_type == "discord.test" and row.status == "pending"

    api.put(f"{N}/preferences", json={"preferences": [{"category": "administrative", "enabled": False}]})
    assert api.post(f"{N}/discord/test").status_code == 400


def test_send_test_message_requires_login(client):
    assert client.post(f"{N}/discord/test").status_code in (401, 403)

