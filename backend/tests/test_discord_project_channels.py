"""Private per-project Discord channels (Discord HTTP is mocked)."""

import json

import httpx
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.notification import DiscordAccount, DiscordProjectChannel, Notification
from app.models.project import ProjectMember
from app.models.research import ResearchPaper
from app.services import discord_project_channels as dpc
from app.services.discord_client import DiscordSender
from app.workers import notification_worker

R = "/api/v1/research"
GUILD = "900"
BOT = "1"


class FakeDiscord:
    """In-memory Discord: records channels and member overwrites."""

    def __init__(self, guild_members=None):
        self.guild_members = guild_members  # None = everyone is in the server
        self.channels: dict[str, dict] = {}
        self.messages: list[tuple[str, str]] = []
        self.threads: list[tuple[str, str]] = []
        self.calls = 0
        self.fail_create = False

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        path = request.url.path.removeprefix("/api/v10")
        body = json.loads(request.content) if request.content else {}
        if request.method == "GET" and path == "/users/@me":
            return httpx.Response(200, json={"id": BOT})
        if request.method == "POST" and path == f"/guilds/{GUILD}/channels":
            if self.fail_create:
                return httpx.Response(403, json={"code": 50013})
            cid = str(1000 + len(self.channels))
            self.channels[cid] = {
                "name": body["name"],
                "overwrites": {o["id"]: o for o in body["permission_overwrites"]},
                "parent_id": body.get("parent_id"),
            }
            return httpx.Response(201, json={"id": cid})
        parts = path.strip("/").split("/")
        if parts[0] == "channels" and parts[1] in self.channels:
            channel = self.channels[parts[1]]
            if request.method == "PATCH" and len(parts) == 2:
                channel["name"] = body["name"]
                return httpx.Response(200, json={})
            if len(parts) == 4 and parts[2] == "permissions":
                user = parts[3]
                if request.method == "PUT":
                    if self.guild_members is not None and user not in self.guild_members:
                        return httpx.Response(404, json={"code": 10013})
                    channel["overwrites"][user] = body | {"id": user}
                    return httpx.Response(204)
                if request.method == "DELETE":
                    if channel["overwrites"].pop(user, None) is None:
                        return httpx.Response(404, json={"code": 10009})
                    return httpx.Response(204)
            if request.method == "POST" and parts[2:] == ["messages"]:
                self.messages.append((parts[1], body["content"]))
                return httpx.Response(200, json={"id": f"m{len(self.messages)}"})
            if request.method == "POST" and len(parts) == 5 and parts[4] == "threads":
                self.threads.append((parts[1], body["name"]))
                return httpx.Response(201, json={"id": "t-1"})
        return httpx.Response(404, json={"code": 0})

    def sender(self) -> DiscordSender:
        return DiscordSender(httpx.Client(transport=httpx.MockTransport(self.handler)))

    def members(self, cid):
        return {k for k, v in self.channels[cid]["overwrites"].items() if v["type"] == 1 and k != BOT}


@pytest.fixture()
def configured(monkeypatch):
    monkeypatch.setattr(settings, "DISCORD_BOT_TOKEN", "test-token")
    monkeypatch.setattr(settings, "DISCORD_GUILD_ID", GUILD)
    monkeypatch.setattr(settings, "DISCORD_PROJECT_CHANNELS", True)
    monkeypatch.setattr(settings, "DISCORD_PROJECT_CATEGORY_ID", "")
    monkeypatch.setattr(settings, "DISCORD_RESEARCH_CHANNEL_ID", "4242")


def _link(db, user, discord_id):
    db.add(DiscordAccount(user_id=user.id, discord_user_id=discord_id, discord_username=f"u{discord_id}"))
    db.commit()


def _row(db, project):
    db.expire_all()
    return db.get(DiscordProjectChannel, project.id)


def test_channel_is_private_and_has_linked_members(db, make_user, make_project, configured):
    owner, member, unlinked = make_user("Student"), make_user("Student"), make_user("Student")
    project = make_project(owner, members=[(member, "member"), (unlinked, "member")], title="Spectral Imaging: Study #2")
    _link(db, owner, "11")
    _link(db, member, "12")
    discord = FakeDiscord()

    dpc.sync_project_channels(db, discord.sender())

    row = _row(db, project)
    channel = discord.channels[row.channel_id]
    assert channel["name"] == row.channel_name == "spectral-imaging-study-2"
    everyone = channel["overwrites"][GUILD]
    assert everyone["type"] == 0 and int(everyone["deny"]) & dpc.VIEW_CHANNEL
    assert int(channel["overwrites"][BOT]["allow"]) & dpc.SEND_MESSAGES
    assert discord.members(row.channel_id) == {"11", "12"}
    assert int(channel["overwrites"]["12"]["allow"]) == dpc.MEMBER_ALLOW
    assert sorted(row.member_discord_ids) == ["11", "12"]

    # Nothing changed: no Discord calls on the next pass.
    before = discord.calls
    dpc.sync_project_channels(db, discord.sender())
    assert discord.calls == before
    assert len(discord.channels) == 1


def test_membership_link_unlink_rename_and_archive(db, make_user, make_project, configured):
    owner, member, late = make_user("Student"), make_user("Student"), make_user("Student")
    project = make_project(owner, members=[(member, "member")])
    _link(db, owner, "21")
    _link(db, member, "22")
    discord = FakeDiscord()
    sender = discord.sender()
    dpc.sync_project_channels(db, sender)
    cid = _row(db, project).channel_id

    # A member is removed, a new one joins and links Discord later.
    db.scalar(select(ProjectMember).where(ProjectMember.user_id == member.id)).membership_status = "removed"
    db.add(ProjectMember(project_id=project.id, user_id=late.id, membership_role="member"))
    db.commit()
    dpc.sync_project_channels(db, sender)
    assert discord.members(cid) == {"21"}
    _link(db, late, "23")
    dpc.sync_project_channels(db, sender)
    assert discord.members(cid) == {"21", "23"}

    # Owner unlinks Discord.
    db.scalar(select(DiscordAccount).where(DiscordAccount.user_id == owner.id)).status = "unlinked"
    project.title = "Renamed Project"
    db.commit()
    dpc.sync_project_channels(db, sender)
    assert discord.members(cid) == {"23"}
    assert discord.channels[cid]["name"] == "renamed-project"

    # Archived: kept, read-only.
    project.status = "archived"
    db.commit()
    dpc.sync_project_channels(db, sender)
    overwrite = discord.channels[cid]["overwrites"]["23"]
    assert int(overwrite["allow"]) == dpc.READ_ONLY_ALLOW and int(overwrite["deny"]) & dpc.SEND_MESSAGES
    assert _row(db, project).access_mode == "read_only"


def test_member_not_in_server_is_retried(db, make_user, make_project, configured):
    owner = make_user("Student")
    project = make_project(owner)
    _link(db, owner, "31")
    discord = FakeDiscord(guild_members=set())
    sender = discord.sender()
    dpc.sync_project_channels(db, sender)
    row = _row(db, project)
    assert row.member_discord_ids == []

    discord.guild_members = {"31"}  # they joined the server
    dpc.sync_project_channels(db, sender)
    assert discord.members(row.channel_id) == {"31"}


def test_no_channels_for_archived_projects_or_when_disabled(db, make_user, make_project, configured, monkeypatch):
    make_project(make_user("Student"), status="archived")
    discord = FakeDiscord()
    dpc.sync_project_channels(db, discord.sender())
    assert discord.channels == {}

    monkeypatch.setattr(settings, "DISCORD_PROJECT_CHANNELS", False)
    make_project(make_user("Student"))
    assert dpc.sync_project_channels(db, discord.sender()) == 0
    assert discord.channels == {}


def test_create_failure_is_retried_later(db, make_user, make_project, configured):
    project = make_project(make_user("Student"))
    discord = FakeDiscord()
    discord.fail_create = True  # bot lacks Manage Channels
    dpc.sync_project_channels(db, discord.sender())
    assert _row(db, project) is None
    discord.fail_create = False
    dpc.sync_project_channels(db, discord.sender())
    assert _row(db, project) is not None


def test_project_paper_goes_to_project_channel_with_thread(db, login, make_user, make_project, configured):
    owner, member = make_user("Student"), make_user("Student")
    project = make_project(owner, members=[(member, "member")])
    _link(db, member, "41")
    discord = FakeDiscord()
    sender = discord.sender()
    dpc.sync_project_channels(db, sender)
    cid = _row(db, project).channel_id

    paper = login(owner).post(f"{R}/papers", json={"title": "Team paper", "project_id": str(project.id)}).json()

    rows = db.scalars(select(Notification)).all()
    assert [(n.event_type, n.channel_id) for n in rows] == [("paper.project_post", cid)]  # no DMs, no #research

    assert notification_worker.run_once(db, sender) == {"sent": 1}
    assert discord.messages[0][0] == cid and "Team paper" in discord.messages[0][1]
    assert discord.threads == [(cid, "Team paper")]
    db.expire_all()
    # The private thread is not exposed as the lab-wide "Discuss on Discord" link.
    assert db.get(ResearchPaper, paper["id"]).discord_thread_id is None


def test_project_without_channel_falls_back_to_dms(db, login, make_user, make_project, configured):
    owner, member = make_user("Student"), make_user("Student")
    project = make_project(owner, members=[(member, "member")])
    _link(db, member, "51")
    login(owner).post(f"{R}/papers", json={"title": "Early paper", "project_id": str(project.id)})
    [dm] = db.scalars(select(Notification)).all()
    assert dm.event_type == "paper.linked" and dm.recipient_id == member.id


def test_channel_name_slug():
    assert dpc.channel_name("  Spectral Imaging: Study #2 ") == "spectral-imaging-study-2"
    assert dpc.channel_name("!!!") == "project"
    assert len(dpc.channel_name("x" * 300)) == 100


def test_invite_permission_integer():
    assert dpc.BOT_GUILD_PERMISSIONS == 309506198608



def test_missing_table_does_not_break_the_callers_transaction(db, make_user, make_project, configured, monkeypatch):
    """Before the migration runs, looking up a channel must not poison the transaction."""

    from sqlalchemy import text

    project = make_project(make_user("Student"))
    real_get = db.get

    def get_without_table(model, *args, **kwargs):
        if model is DiscordProjectChannel:
            db.execute(text("SELECT * FROM table_that_does_not_exist"))
        return real_get(model, *args, **kwargs)

    monkeypatch.setattr(db, "get", get_without_table)
    assert dpc.channel_for_project(db, project.id) is None
    assert db.scalar(text("SELECT 1")) == 1  # transaction still usable
