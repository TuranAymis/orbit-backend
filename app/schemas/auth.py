from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, StringConstraints

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
    full_name: str = Field(..., min_length=2, max_length=255)
    email: OrbitEmail
    password: str = Field(..., min_length=6, max_length=128)
    membership_level: MembershipLevel = MembershipLevel.FREE


class LoginRequest(BaseModel):
    email: OrbitEmail
    password: str = Field(..., min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
