from pydantic import BaseModel, EmailStr, Field

from app.utils.enums import MembershipLevel


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    membership_level: MembershipLevel = MembershipLevel.FREE


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
