from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.utils.enums import ChatRoomType


class ChatRoomIdentity(BaseModel):
    room_type: ChatRoomType
    room_id: UUID


class ChatRoomReadRequest(ChatRoomIdentity):
    last_read_message_id: UUID | None = None


class ChatRoomMuteRequest(ChatRoomIdentity):
    pass


class ChatRoomStateResponse(BaseModel):
    room_type: ChatRoomType
    room_id: UUID
    is_muted: bool
    last_read_message_id: UUID | None = None
    last_read_at: datetime | None = None
    unread_count: int


class ChatRoomReadResponse(ChatRoomStateResponse):
    success: bool = True


class ChatRoomMuteResponse(BaseModel):
    success: bool = True
    room_type: ChatRoomType
    room_id: UUID
    is_muted: bool


class ChatRoomUnreadCountResponse(BaseModel):
    room_type: ChatRoomType
    room_id: UUID
    unread_count: int
    is_muted: bool


class ChatRoomUnreadSummaryItem(BaseModel):
    room_type: ChatRoomType
    room_id: UUID
    unread_count: int
    is_muted: bool


class ChatRoomUnreadSummaryResponse(BaseModel):
    total_unread_count: int
    rooms: list[ChatRoomUnreadSummaryItem]


class ChatRoomStateQuery(ChatRoomIdentity):
    model_config = ConfigDict(from_attributes=True)


class ChatRoomUnreadCountQuery(ChatRoomIdentity):
    model_config = ConfigDict(from_attributes=True)


class ChatRoomMuteQuery(BaseModel):
    room_type: ChatRoomType
    room_id: UUID
