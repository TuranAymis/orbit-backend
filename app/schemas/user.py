from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
)

from app.utils.enums import MembershipLevel


OrbitEmail = EmailStr | Annotated[
    str,
    StringConstraints(
        pattern=r"^[^@\s]+@[^@\s]+\.local$",
        strip_whitespace=True,
        to_lower=True,
    ),
]


class UserBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: OrbitEmail


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bio: str | None = None
    location: str | None = None
    avatar_url: str | None = None
    membership_level: MembershipLevel
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: OrbitEmail
    full_name: str
    bio: str | None = None
    location: str | None = None
    avatar_url: str | None = None
    is_active: bool
    membership_level: MembershipLevel
    created_at: datetime
    updated_at: datetime


class UserMeResponse(ProfileResponse):
    pass


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    bio: str | None = Field(default=None, max_length=2000)
    location: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=2048)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        trimmed_value = value.strip()
        if not trimmed_value:
            raise ValueError("full_name must not be empty.")
        return trimmed_value

    @field_validator("bio", "location", "avatar_url")
    @classmethod
    def normalize_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()
