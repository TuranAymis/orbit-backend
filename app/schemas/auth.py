from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator

from app.utils.enums import MembershipLevel


OrbitEmail = EmailStr | Annotated[
    str,
    StringConstraints(
        pattern=r"^[^@\s]+@[^@\s]+\.local$",
        strip_whitespace=True,
        to_lower=True,
    ),
]


class RegisterRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    email: OrbitEmail
    password: str = Field(..., min_length=6, max_length=128)
    membership_level: MembershipLevel = MembershipLevel.FREE

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed_value = value.strip()
        if len(trimmed_value) < 2:
            raise ValueError("full_name must be at least 2 characters long.")
        return trimmed_value


class LoginRequest(BaseModel):
    email: OrbitEmail
    password: str = Field(..., min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthActionResponse(BaseModel):
    success: bool = True
    message: str


class VerifyEmailRequest(BaseModel):
    email: OrbitEmail
    code: str = Field(..., min_length=6, max_length=6)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        trimmed_value = value.strip()
        if not trimmed_value.isdigit():
            raise ValueError("code must contain only digits.")
        return trimmed_value


class ResendVerificationCodeRequest(BaseModel):
    email: OrbitEmail
