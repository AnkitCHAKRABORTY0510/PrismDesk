"""Reusable column factories shared by the Prism Desk models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


def user_fk(
    nullable: bool = False,
    ondelete: str = "SET NULL",
    index: bool = False,
) -> Mapped:
    return mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete=ondelete),
        nullable=nullable,
        index=index,
    )


def created_at() -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


def updated_at() -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


def optional_timestamp() -> Mapped[datetime | None]:
    return mapped_column(DateTime(timezone=True), nullable=True)
