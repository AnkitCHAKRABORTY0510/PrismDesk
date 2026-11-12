import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.notification import DiscordAccount, Notification
from app.models.research import ResearchPaper
from app.services.discord_client import DeliveryResult
from app.workers import notification_worker

R = "/api/v1/research"


@pytest.fixture()
def discord_configured(monkeypatch):
    monkeypatch.setattr(settings, "DISCORD_BOT_TOKEN", "test-token")
    monkeypatch.setattr(settings, "DISCORD_RESEARCH_CHANNEL_ID", "4242")
    monkeypatch.setattr(settings, "DISCORD_GUILD_ID", "777")


class ThreadSender:
    def __init__(self):
        self.threads = []

    def open_dm_channel(self, discord_user_id):
        return DeliveryResult(True, 200, channel_id="dm")

    def send_message(self, channel_id, content):
        return DeliveryResult(True, 200, message_id="msg-1")

    def start_thread(self, channel_id, message_id, name):
        self.threads.append((channel_id, message_id, name))
        return DeliveryResult(True, 201, channel_id="thread-9")


def test_new_paper_posts_to_channel_and_opens_thread(db, login, student, discord_configured):
    paper = login(student).post(f"{R}/papers", json={"title": "Sparse coding", "doi": "10.1000/sparse"}).json()
    queued = db.scalar(select(Notification).where(Notification.event_type == "paper.added"))
    assert queued.channel_id == "4242" and "Sparse coding" in queued.title
    assert "https://doi.org/10.1000/sparse" in queued.body

    sender = ThreadSender()
    assert notification_worker.run_once(db, sender) == {"sent": 1}
    assert sender.threads == [("4242", "msg-1", "Sparse coding")]
    db.expire_all()
    assert db.get(ResearchPaper, paper["id"]).discord_thread_id == "thread-9"

    detail = login(student).get(f"{R}/papers/{paper['id']}").json()
    assert detail["discord_thread_url"] == "https://discord.com/channels/777/thread-9"


def test_no_channel_post_without_configuration(db, login, student, monkeypatch):
    monkeypatch.setattr(settings, "DISCORD_RESEARCH_CHANNEL_ID", "")
    login(student).post(f"{R}/papers", json={"title": "Quiet paper"})
    assert db.scalar(select(Notification).where(Notification.event_type == "paper.added")) is None


def test_thread_failure_does_not_fail_the_post(db, login, student, discord_configured):
    login(student).post(f"{R}/papers", json={"title": "Thread fails"})

    class NoThread(ThreadSender):
        def start_thread(self, channel_id, message_id, name):
            return DeliveryResult(False, 403, "Missing permissions", retryable=False)

    assert notification_worker.run_once(db, NoThread()) == {"sent": 1}


def test_linking_paper_notifies_project_members(db, login, make_user, make_project, discord_configured):
    owner = make_user("Student")
    member = make_user("Student")
    project = make_project(owner, members=[(member, "member")])
    db.add(DiscordAccount(user_id=member.id, discord_user_id="555", discord_username="m"))
    db.commit()

    login(owner).post(f"{R}/papers", json={"title": "Shared paper", "project_id": str(project.id)})
    dm = db.scalar(select(Notification).where(Notification.recipient_id == member.id))
    assert dm.event_type == "paper.linked" and dm.category == "research"
    assert db.scalar(select(Notification).where(Notification.recipient_id == owner.id)) is None
