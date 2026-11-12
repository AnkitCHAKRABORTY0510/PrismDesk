from datetime import date, datetime, timedelta, timezone

H = "/api/v1/handbook"
TODAY = date.today()


def _iso(day: date) -> str:
    return day.isoformat()


def test_pins_are_private_and_allow_future_dates(login, make_user):
    student = make_user("Student")
    other = make_user("Student")
    api = login(student)
    future = TODAY + timedelta(days=40)

    created = api.post(f"{H}/pins", json={"pin_date": _iso(future), "label": "  Camera-ready  ", "category": "deadline"})
    assert created.status_code == 201, created.text
    pin = created.json()
    assert pin["label"] == "Camera-ready"

    assert api.post(f"{H}/pins", json={"pin_date": _iso(TODAY), "label": "x", "category": "party"}).status_code == 422
    assert api.post(f"{H}/pins", json={"pin_date": _iso(TODAY), "label": "   "}).status_code == 422

    in_range = api.get(f"{H}/planner", params={"date_from": _iso(TODAY), "date_to": _iso(future)}).json()
    assert [p["id"] for p in in_range["pins"]] == [pin["id"]]

    # Another user can neither see nor touch it.
    other_api = login(other)
    assert other_api.get(f"{H}/planner", params={"date_from": _iso(TODAY), "date_to": _iso(future)}).json()["pins"] == []
    assert other_api.patch(f"{H}/pins/{pin['id']}", json={"label": "Mine"}).status_code == 404
    assert other_api.delete(f"{H}/pins/{pin['id']}").status_code == 404

    updated = api.patch(f"{H}/pins/{pin['id']}", json={"category": "milestone", "note": "Submit PDF"}).json()
    assert updated["category"] == "milestone" and updated["note"] == "Submit PDF"
    assert api.delete(f"{H}/pins/{pin['id']}").status_code == 204
    assert api.patch(f"{H}/pins/{pin['id']}", json={"label": "Gone"}).status_code == 404


def test_planner_range_validation(login, make_user):
    api = login(make_user("Student"))
    assert api.get(f"{H}/planner", params={"date_from": _iso(TODAY), "date_to": _iso(TODAY - timedelta(days=1))}).status_code == 400
    assert api.get(f"{H}/planner", params={"date_from": _iso(TODAY), "date_to": _iso(TODAY + timedelta(days=500))}).status_code == 400


def test_guests_have_no_planner(login, make_user):
    api = login(make_user("Guest"))
    assert api.get(f"{H}/planner", params={"date_from": _iso(TODAY), "date_to": _iso(TODAY)}).status_code == 403
    assert api.post(f"{H}/todos", json={"todo_date": _iso(TODAY), "text": "x"}).status_code == 403


def test_supervisors_can_plan_too(login, make_user):
    api = login(make_user("Professor"))
    assert api.post(f"{H}/todos", json={"todo_date": _iso(TODAY), "text": "Review drafts"}).status_code == 201


def test_todos_order_complete_reorder_and_carry_forward(login, make_user):
    student = make_user("Student")
    api = login(student)
    tomorrow = TODAY + timedelta(days=1)

    ids = [api.post(f"{H}/todos", json={"todo_date": _iso(TODAY), "text": text}).json()["id"] for text in ("A", "B", "C")]
    planner = api.get(f"{H}/planner", params={"date_from": _iso(TODAY), "date_to": _iso(TODAY)}).json()
    assert [t["text"] for t in planner["todos"]] == ["A", "B", "C"]

    done = api.patch(f"{H}/todos/{ids[1]}", json={"done": True}).json()
    assert done["done"] is True and done["done_at"] is not None
    undone = api.patch(f"{H}/todos/{ids[1]}", json={"done": False}).json()
    assert undone["done_at"] is None
    api.patch(f"{H}/todos/{ids[1]}", json={"done": True})

    reordered = api.post(f"{H}/todos/reorder", json={"todo_date": _iso(TODAY), "ids": [ids[2], ids[0], ids[1]]})
    assert [t["text"] for t in reordered.json()] == ["C", "A", "B"]
    # Partial or duplicated lists are rejected.
    assert api.post(f"{H}/todos/reorder", json={"todo_date": _iso(TODAY), "ids": [ids[0]]}).status_code == 400
    assert api.post(f"{H}/todos/reorder", json={"todo_date": _iso(TODAY), "ids": [ids[0], ids[0], ids[2]]}).status_code == 400

    api.post(f"{H}/todos", json={"todo_date": _iso(tomorrow), "text": "Existing"})
    moved = api.post(f"{H}/todos/carry-forward", json={"from_date": _iso(TODAY), "to_date": _iso(tomorrow)})
    assert [t["text"] for t in moved.json()] == ["C", "A"]
    assert api.post(f"{H}/todos/carry-forward", json={"from_date": _iso(TODAY), "to_date": _iso(TODAY)}).status_code == 400

    planner = api.get(f"{H}/planner", params={"date_from": _iso(TODAY), "date_to": _iso(tomorrow)}).json()
    by_day = {}
    for todo in planner["todos"]:
        by_day.setdefault(todo["todo_date"], []).append(todo["text"])
    assert by_day == {_iso(TODAY): ["B"], _iso(tomorrow): ["Existing", "C", "A"]}

    assert [t["text"] for t in api.get(f"{H}/todos/open").json()] == ["Existing", "C", "A"]
    assert login(make_user("Student")).patch(f"{H}/todos/{ids[0]}", json={"done": True}).status_code == 404
    assert api.delete(f"{H}/todos/{ids[0]}").status_code == 204


def test_reminders_upcoming_and_dismiss(login, make_user):
    api = login(make_user("Student"))
    now = datetime.now(timezone.utc)
    due = api.post(
        f"{H}/reminders",
        json={"reminder_date": _iso(TODAY), "remind_at": (now - timedelta(minutes=5)).isoformat(), "note": "Stand-up"},
    ).json()
    later = api.post(
        f"{H}/reminders",
        json={"reminder_date": _iso(TODAY + timedelta(days=3)), "remind_at": (now + timedelta(days=3)).isoformat(), "note": "Send draft"},
    ).json()
    old = api.post(
        f"{H}/reminders",
        json={"reminder_date": _iso(TODAY - timedelta(days=30)), "remind_at": (now - timedelta(days=30)).isoformat(), "note": "Old"},
    ).json()

    upcoming = [r["id"] for r in api.get(f"{H}/reminders/upcoming").json()]
    assert upcoming == [due["id"], later["id"]]
    assert old["id"] not in upcoming

    dismissed = api.patch(f"{H}/reminders/{due['id']}", json={"dismissed": True}).json()
    assert dismissed["dismissed_at"] is not None
    assert [r["id"] for r in api.get(f"{H}/reminders/upcoming").json()] == [later["id"]]

    # Snoozing (moving the time) re-arms a dismissed reminder.
    snoozed = api.patch(f"{H}/reminders/{due['id']}", json={"remind_at": (now + timedelta(minutes=10)).isoformat()}).json()
    assert snoozed["dismissed_at"] is None

    assert api.post(f"{H}/reminders", json={"reminder_date": _iso(TODAY), "remind_at": now.isoformat(), "note": " "}).status_code == 422
    assert login(make_user("Student")).delete(f"{H}/reminders/{later['id']}").status_code == 404
    assert api.delete(f"{H}/reminders/{later['id']}").status_code == 204


def test_future_entries_and_summaries_stay_blocked(login, make_user):
    api = login(make_user("Student"))
    future = _iso(TODAY + timedelta(days=5))
    assert api.post(f"{H}/summaries", json={"entry_date": future, "summary": "Plan"}).status_code == 400
    assert api.post(f"{H}/todos", json={"todo_date": future, "text": "Plan"}).status_code == 201
