"""Personal handbook planner: pins, to-dos and reminders.

Every row belongs to one user and is only ever read or changed by that
user; another user's id behaves exactly like a missing row (404). Future
dates are allowed because the planner is for planning ahead.
"""

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import BadRequestError, NotFoundError
from app.models.handbook import HandbookPin, HandbookReminder, HandbookTodo
from app.models.user import User
from app.schemas.handbook_planner import (
    PinCreate,
    PinUpdate,
    ReminderCreate,
    ReminderUpdate,
    TodoCarryForward,
    TodoCreate,
    TodoReorder,
    TodoUpdate,
)

MAX_RANGE_DAYS = 400
MAX_ROWS_PER_DAY = 100


def _commit(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _own(db: Session, model, user: User, row_id: UUID):
    row = db.scalar(select(model).where(model.id == row_id, model.owner_id == user.id))
    if row is None:
        raise NotFoundError("Item not found.")
    return row


def _check_range(date_from: date, date_to: date) -> None:
    if date_to < date_from:
        raise BadRequestError("The end date must not be before the start date.")
    if (date_to - date_from).days > MAX_RANGE_DAYS:
        raise BadRequestError(f"Ask for at most {MAX_RANGE_DAYS} days at a time.")


def planner_range(db: Session, user: User, date_from: date, date_to: date):
    _check_range(date_from, date_to)
    pins = db.scalars(
        select(HandbookPin)
        .where(HandbookPin.owner_id == user.id, HandbookPin.pin_date.between(date_from, date_to))
        .order_by(HandbookPin.pin_date, HandbookPin.created_at)
    ).all()
    todos = db.scalars(
        select(HandbookTodo)
        .where(HandbookTodo.owner_id == user.id, HandbookTodo.todo_date.between(date_from, date_to))
        .order_by(HandbookTodo.todo_date, HandbookTodo.position, HandbookTodo.created_at)
    ).all()
    reminders = db.scalars(
        select(HandbookReminder)
        .where(HandbookReminder.owner_id == user.id, HandbookReminder.reminder_date.between(date_from, date_to))
        .order_by(HandbookReminder.remind_at)
    ).all()
    return list(pins), list(todos), list(reminders)


# --- Pins ----------------------------------------------------------------------------


def _day_count(db: Session, model, date_column, user: User, day: date) -> int:
    return db.scalar(select(func.count()).select_from(model).where(model.owner_id == user.id, date_column == day)) or 0


def create_pin(db: Session, user: User, data: PinCreate) -> HandbookPin:
    if _day_count(db, HandbookPin, HandbookPin.pin_date, user, data.pin_date) >= MAX_ROWS_PER_DAY:
        raise BadRequestError("That day already has too many pins.")
    pin = HandbookPin(owner_id=user.id, **data.model_dump())
    pin.note = pin.note.strip()
    db.add(pin)
    _commit(db)
    db.refresh(pin)
    return pin


def update_pin(db: Session, user: User, pin_id: UUID, data: PinUpdate) -> HandbookPin:
    pin = _own(db, HandbookPin, user, pin_id)
    for field, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(pin, field, value.strip() if isinstance(value, str) and field == "note" else value)
    _commit(db)
    db.refresh(pin)
    return pin


def delete_pin(db: Session, user: User, pin_id: UUID) -> None:
    db.delete(_own(db, HandbookPin, user, pin_id))
    _commit(db)


# --- To-dos --------------------------------------------------------------------------


def _next_position(db: Session, user: User, day: date) -> int:
    current = db.scalar(
        select(func.max(HandbookTodo.position)).where(HandbookTodo.owner_id == user.id, HandbookTodo.todo_date == day)
    )
    return 0 if current is None else current + 1


def create_todo(db: Session, user: User, data: TodoCreate) -> HandbookTodo:
    if _day_count(db, HandbookTodo, HandbookTodo.todo_date, user, data.todo_date) >= MAX_ROWS_PER_DAY:
        raise BadRequestError("That day already has too many to-dos.")
    todo = HandbookTodo(
        owner_id=user.id,
        todo_date=data.todo_date,
        text=data.text,
        position=_next_position(db, user, data.todo_date),
    )
    db.add(todo)
    _commit(db)
    db.refresh(todo)
    return todo


def update_todo(db: Session, user: User, todo_id: UUID, data: TodoUpdate) -> HandbookTodo:
    todo = _own(db, HandbookTodo, user, todo_id)
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    if "todo_date" in changes and changes["todo_date"] != todo.todo_date:
        todo.todo_date = changes["todo_date"]
        todo.position = _next_position(db, user, todo.todo_date)
    if "text" in changes:
        todo.text = changes["text"]
    if "done" in changes and changes["done"] != todo.done:
        todo.done = changes["done"]
        todo.done_at = datetime.now(timezone.utc) if todo.done else None
    _commit(db)
    db.refresh(todo)
    return todo


def delete_todo(db: Session, user: User, todo_id: UUID) -> None:
    db.delete(_own(db, HandbookTodo, user, todo_id))
    _commit(db)


def reorder_todos(db: Session, user: User, data: TodoReorder) -> list[HandbookTodo]:
    todos = db.scalars(
        select(HandbookTodo).where(HandbookTodo.owner_id == user.id, HandbookTodo.todo_date == data.todo_date)
    ).all()
    by_id = {todo.id: todo for todo in todos}
    if len(set(data.ids)) != len(data.ids) or set(data.ids) != set(by_id):
        raise BadRequestError("Send every to-do of that day exactly once.")
    for position, todo_id in enumerate(data.ids):
        by_id[todo_id].position = position
    _commit(db)
    return sorted(todos, key=lambda todo: todo.position)


def carry_forward(db: Session, user: User, data: TodoCarryForward) -> list[HandbookTodo]:
    """Move the unfinished to-dos of one day to the end of another day's list."""

    if data.to_date <= data.from_date:
        raise BadRequestError("Unfinished to-dos can only be carried forward to a later day.")
    open_todos = db.scalars(
        select(HandbookTodo)
        .where(
            HandbookTodo.owner_id == user.id,
            HandbookTodo.todo_date == data.from_date,
            HandbookTodo.done.is_(False),
        )
        .order_by(HandbookTodo.position, HandbookTodo.created_at)
    ).all()
    position = _next_position(db, user, data.to_date)
    for offset, todo in enumerate(open_todos):
        todo.todo_date = data.to_date
        todo.position = position + offset
    _commit(db)
    return list(open_todos)


def open_todos(db: Session, user: User, limit: int) -> list[HandbookTodo]:
    return list(
        db.scalars(
            select(HandbookTodo)
            .where(HandbookTodo.owner_id == user.id, HandbookTodo.done.is_(False))
            .order_by(HandbookTodo.todo_date, HandbookTodo.position)
            .limit(limit)
        ).all()
    )


# --- Reminders -----------------------------------------------------------------------


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def create_reminder(db: Session, user: User, data: ReminderCreate) -> HandbookReminder:
    if _day_count(db, HandbookReminder, HandbookReminder.reminder_date, user, data.reminder_date) >= MAX_ROWS_PER_DAY:
        raise BadRequestError("That day already has too many reminders.")
    reminder = HandbookReminder(
        owner_id=user.id,
        reminder_date=data.reminder_date,
        remind_at=_aware(data.remind_at),
        note=data.note,
    )
    db.add(reminder)
    _commit(db)
    db.refresh(reminder)
    return reminder


def update_reminder(db: Session, user: User, reminder_id: UUID, data: ReminderUpdate) -> HandbookReminder:
    reminder = _own(db, HandbookReminder, user, reminder_id)
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    dismissed = changes.pop("dismissed", None)
    if "remind_at" in changes:
        changes["remind_at"] = _aware(changes["remind_at"])
        # Moving a reminder re-arms it.
        reminder.dismissed_at = None
    for field, value in changes.items():
        setattr(reminder, field, value)
    if dismissed is not None:
        reminder.dismissed_at = datetime.now(timezone.utc) if dismissed else None
    _commit(db)
    db.refresh(reminder)
    return reminder


def delete_reminder(db: Session, user: User, reminder_id: UUID) -> None:
    db.delete(_own(db, HandbookReminder, user, reminder_id))
    _commit(db)


def upcoming_reminders(db: Session, user: User, limit: int, overdue_days: int = 7) -> list[HandbookReminder]:
    """Active reminders: due ones not yet dismissed (last week) and future ones."""

    since = datetime.now(timezone.utc) - timedelta(days=overdue_days)
    return list(
        db.scalars(
            select(HandbookReminder)
            .where(
                HandbookReminder.owner_id == user.id,
                HandbookReminder.dismissed_at.is_(None),
                HandbookReminder.remind_at >= since,
            )
            .order_by(HandbookReminder.remind_at)
            .limit(limit)
        ).all()
    )
