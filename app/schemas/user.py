from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.utils.enums import MembershipLevel


class UserBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    membership_level: MembershipLevel
    is_active: bool
    created_at: datetime
    updated_at: datetime
