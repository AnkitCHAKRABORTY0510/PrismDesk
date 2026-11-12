"""Schemas for the personal handbook planner (pins, to-dos, reminders)."""

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, BaseModel, Field

PinCategory = Literal["deadline", "meeting", "milestone", "idea", "other"]


def _strip_required(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("This field cannot be empty.")
    return value


Label = Annotated[str, Field(min_length=1, max_length=120), AfterValidator(_strip_required)]
ShortText = Annotated[str, Field(min_length=1, max_length=500), AfterValidator(_strip_required)]


class PinCreate(BaseModel):
    pin_date: date
    label: Label
    category: PinCategory = "other"
    note: str = Field(default="", max_length=2000)



class PinUpdate(BaseModel):
    pin_date: date | None = None
    label: Label | None = None
    category: PinCategory | None = None
    note: str | None = Field(default=None, max_length=2000)



class PinResponse(BaseModel):
    id: UUID
    pin_date: date
    label: str
    category: str
    note: str
    created_at: datetime
    updated_at: datetime


class TodoCreate(BaseModel):
    todo_date: date
    text: ShortText



class TodoUpdate(BaseModel):
    todo_date: date | None = None
    text: ShortText | None = None
    done: bool | None = None



class TodoReorder(BaseModel):
    todo_date: date
    ids: list[UUID] = Field(max_length=500)


class TodoCarryForward(BaseModel):
    from_date: date
    to_date: date


class TodoResponse(BaseModel):
    id: UUID
    todo_date: date
    text: str
    done: bool
    position: int
    done_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ReminderCreate(BaseModel):
    reminder_date: date
    remind_at: datetime
    note: ShortText



class ReminderUpdate(BaseModel):
    reminder_date: date | None = None
    remind_at: datetime | None = None
    note: ShortText | None = None
    dismissed: bool | None = None



class ReminderResponse(BaseModel):
    id: UUID
    reminder_date: date
    remind_at: datetime
    note: str
    dismissed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PlannerRange(BaseModel):
    pins: list[PinResponse]
    todos: list[TodoResponse]
    reminders: list[ReminderResponse]
