"""Reminders: users nudging other users, with a private Discord DM."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.notification import DiscordAccount, Notification

T = "/api/v1/tasks"


def _future(days=3):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _link_discord(db, user, discord_id):
    db.add(DiscordAccount(user_id=user.id, discord_user_id=discord_id, discord_username=f"u{discord_id}"))
    db.commit()


def _setup(login, make_user, make_project):
    professor = make_user("Professor")
    student = make_user("Student")
    other = make_user("Student")
    project = make_project(student, members=[(professor, "supervisor"), (other, "member")])
    task = login(professor).post(
        T,
        json={"task_type": "official", "title": "Literature survey", "project_id": str(project.id), "due_at": _future(), "assignee_ids": [str(student.id)]},
    ).json()
    return professor, student, other, project, task


def test_assigning_official_work_sends_private_dm(login, make_user, make_project, db):
    professor = make_user("Professor")
    student = make_user("Student")
    project = make_project(student, members=[(professor, "supervisor")])
    _link_discord(db, student, "9001")

    task = login(professor).post(
        T, json={"task_type": "official", "title": "Calibrate", "project_id": str(project.id), "assignee_ids": [str(student.id)]}
    ).json()
    note = db.scalar(select(Notification).where(Notification.event_type == "task.assigned", Notification.entity_id == task["id"]))
    assert note.recipient_id == student.id and note.channel_id is None  # DM, not a channel
    assert professor.full_name in note.body and "Calibrate" in note.body


def test_student_reminds_professor_about_their_task(login, make_user, make_project, db):
    professor, student, other, project, task = _setup(login, make_user, make_project)
    _link_discord(db, professor, "9002")

    recipients = login(student).get(f"{T}/reminder-recipients", params={"related_task_id": task["id"]}).json()
    assert [r["user"]["id"] for r in recipients] == [str(professor.id)]  # professors only, not other students

    response = login(student).post(
        T,
        json={
            "task_type": "reminder",
            "title": "Please review my survey",
            "description": "Submitted yesterday.",
            "related_task_id": task["id"],
            "assignee_ids": [str(professor.id)],
        },
    )
    assert response.status_code == 201, response.text
    reminder = response.json()
    assert reminder["task_type"] == "reminder"
    assert reminder["project_id"] == str(project.id)
    assert reminder["related_task_title"] == "Literature survey"
    assert reminder["created_by_user"]["id"] == str(student.id)
    assert reminder["can_manage"] is True

    note = db.scalar(select(Notification).where(Notification.event_type == "task.reminder"))
    assert note.recipient_id == professor.id and note.channel_id is None
    assert "Literature survey" in note.body and "Submitted yesterday." in note.body
    assert db.scalar(select(AuditLog).where(AuditLog.action == "task.reminder_sent")) is not None

    # The professor sees it under reminders and can tick it off; the other student can't see it.
    received = login(professor).get(T, params={"scope": "reminders"}).json()["items"]
    assert [r["id"] for r in received] == [reminder["id"]]
    mine = received[0]["my_assignment"]
    assert login(professor).patch(f"{T}/assignments/{mine['id']}/status", json={"status": "completed"}).json()["status"] == "completed"
    assert login(other).get(f"{T}/{reminder['id']}").status_code == 404
    sent = login(student).get(T, params={"scope": "reminders"}).json()["items"]
    assert sent[0]["assignments"][0]["status"] == "completed"


def test_student_reminder_rules(login, make_user, make_project):
    professor, student, other, project, task = _setup(login, make_user, make_project)
    api = login(student)
    base = {"task_type": "reminder", "title": "Nudge"}

    # Only professors may receive a student's reminder.
    assert api.post(T, json={**base, "related_task_id": task["id"], "assignee_ids": [str(other.id)]}).status_code == 400
    # Students must point at a particular task.
    assert api.post(T, json={**base, "project_id": str(project.id), "assignee_ids": [str(professor.id)]}).status_code == 400
    # ...that is assigned to them.
    assert login(other).post(T, json={**base, "related_task_id": task["id"], "assignee_ids": [str(professor.id)]}).status_code == 403
    # Reminders need recipients.
    assert api.post(T, json={**base, "related_task_id": task["id"]}).status_code == 422


def test_professor_reminds_any_member_and_guests_cannot(login, make_user, make_project, db):
    professor, student, other, project, task = _setup(login, make_user, make_project)
    guest = make_user("Guest")
    from app.models.project import ProjectMember

    db.add(ProjectMember(project_id=project.id, user_id=guest.id, membership_role="guest"))
    db.commit()

    names = {r["user"]["id"] for r in login(professor).get(f"{T}/reminder-recipients", params={"project_id": str(project.id)}).json()}
    assert names == {str(student.id), str(other.id)}  # members, not guests or self

    response = login(professor).post(
        T,
        json={"task_type": "reminder", "title": "Group meeting at 4", "project_id": str(project.id), "due_at": _future(1), "assignee_ids": [str(student.id), str(other.id)]},
    )
    assert response.status_code == 201, response.text
    assert len(response.json()["assignments"]) == 2
    assert login(guest).post(
        T, json={"task_type": "reminder", "title": "x", "project_id": str(project.id), "assignee_ids": [str(professor.id)]}
    ).status_code == 403

    # Reminders stay out of the official pipeline and the deadline list.
    dash = login(student).get("/api/v1/dashboard/student").json()
    assert dash["assigned_tasks"]["total"] == 1
    assert [d["title"] for d in dash["upcoming_deadlines"]] == ["Literature survey"]
    assert dash["open_reminders"] == 1


def test_archived_project_blocks_reminders(login, make_user, make_project, db):
    professor, student, other, project, task = _setup(login, make_user, make_project)
    project.status = "archived"
    db.commit()
    assert login(student).post(
        T, json={"task_type": "reminder", "title": "x", "related_task_id": task["id"], "assignee_ids": [str(professor.id)]}
    ).status_code == 403
