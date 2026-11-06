import re
import uuid

from datetime import datetime
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


class RegisterRequest(BaseModel):

    username: str = Field(
        min_length=3,
        max_length=50,
    )

    email: EmailStr

    full_name: str = Field(
        min_length=1,
        max_length=150,
    )

    password: str = Field(
        min_length=12,
        max_length=128,
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip().lower()

        if not re.fullmatch(r"[a-z0-9_.-]+", value):
            raise ValueError(
                "Username can contain only letters, numbers, "
                "underscores, periods and hyphens."
            )

        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Full name cannot be empty.")

        return value


class RegisterResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: EmailStr
    full_name: str
    account_status: str
    created_at: datetime


class LoginRequest(BaseModel):

    identifier: str = Field(
        min_length=3,
        max_length=255,
        description="Username or email address",
    )

    password: str = Field(
        min_length=1,
        max_length=128,
    )

    @field_validator("identifier")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        return value.strip().lower()


class LoginResponse(BaseModel):

    id: uuid.UUID
    username: str
    email: EmailStr
    full_name: str
    roles: list[str]
    capabilities: list[str] = []
    csrf_token: str | None = None
    message: str