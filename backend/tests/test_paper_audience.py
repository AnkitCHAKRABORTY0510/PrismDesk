"""Who hears about a new paper: the project team, or the whole lab."""

from sqlalchemy import select

from app.models.notification import DiscordAccount, Notification
from tests.test_paper_discord import discord_configured  # noqa: F401  (fixture)

R = "/api/v1/research"


def _link(db, user, discord_id):
    db.add(DiscordAccount(user_id=user.id, discord_user_id=discord_id, discord_username=f"u{discord_id}"))
    db.commit()


def _dms(db, user):
    return db.scalars(select(Notification).where(Notification.recipient_id == user.id)).all()


def _channel_posts(db):
    return db.scalars(select(Notification).where(Notification.channel_id.is_not(None))).all()


def test_project_paper_reaches_only_the_team(db, login, make_user, make_project, discord_configured):  # noqa: F811
    owner, teammate, outsider = make_user("Student"), make_user("Student"), make_user("Student")
    project = make_project(owner, members=[(teammate, "member")])
    for i, user in enumerate((owner, teammate, outsider)):
        _link(db, user, str(100 + i))

    response = login(owner).post(f"{R}/papers", json={"title": "Team-only paper", "project_id": str(project.id)})
    assert response.status_code == 201

    assert [n.event_type for n in _dms(db, teammate)] == ["paper.linked"]
    assert _dms(db, outsider) == [] and _dms(db, owner) == []
    assert _channel_posts(db) == []  # not posted to the lab-wide channel


def test_general_paper_reaches_every_lab_member(db, login, make_user, discord_configured):  # noqa: F811
    professor, student, other, unlinked, guest = (
        make_user("Professor"), make_user("Student"), make_user("Student"), make_user("Student"), make_user("Guest"),
    )
    for i, user in enumerate((professor, student, other, guest)):
        _link(db, user, str(200 + i))

    response = login(professor).post(f"{R}/papers", json={"title": "Lab reading", "doi": "10.1000/lab"})
    assert response.status_code == 201

    for user in (student, other):
        [dm] = _dms(db, user)
        assert dm.event_type == "paper.shared" and dm.category == "research" and "Lab reading" in dm.title
    assert _dms(db, professor) == []  # not told about their own paper
    assert _dms(db, unlinked) == [] and _dms(db, guest) == []
    [post] = _channel_posts(db)
    assert post.event_type == "paper.added" and post.channel_id == "4242"


def test_general_paper_respects_research_opt_out(db, login, make_user, discord_configured):  # noqa: F811
    professor, student = make_user("Professor"), make_user("Student")
    _link(db, student, "300")
    login(student).put("/api/v1/notifications/preferences", json={"preferences": [{"category": "research", "enabled": False}]})

    login(professor).post(f"{R}/papers", json={"title": "Muted"})
    assert _dms(db, student) == []


def test_video_link_is_worded_as_video(db, login, make_user, discord_configured):  # noqa: F811
    professor, student = make_user("Professor"), make_user("Student")
    _link(db, student, "400")

    response = login(professor).post(
        f"{R}/papers", json={"title": "Diffusion models lecture", "url": "https://www.youtube.com/watch?v=abc123"}
    )
    assert response.status_code == 201
    [dm] = _dms(db, student)
    assert dm.title.startswith("New video") and "youtube.com" in dm.body
    [post] = _channel_posts(db)
    assert post.title.startswith("🎬 New video")
