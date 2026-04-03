from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.utils.enums import MembershipRole, MembershipStatus


class MembershipCreate(BaseModel):
    user_id: UUID | None = None
    role: MembershipRole = MembershipRole.MEMBER
    status: MembershipStatus = MembershipStatus.PENDING


class MembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    group_id: UUID
    role: MembershipRole
    status: MembershipStatus
    joined_at: datetime
