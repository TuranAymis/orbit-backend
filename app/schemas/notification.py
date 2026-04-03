from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class NotificationRead(BaseModel):
    id: UUID
    type: str
    title: str
    message: str
    created_at: datetime
    is_read: bool
    related_entity_type: str | None = None
    related_entity_id: UUID | None = None


class NotificationUnreadCountResponse(BaseModel):
    count: int


class NotificationMarkReadResponse(BaseModel):
    success: bool
