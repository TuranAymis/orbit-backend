from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession
from app.schemas.chat_room import (
    ChatRoomMuteRequest,
    ChatRoomMuteResponse,
    ChatRoomReadRequest,
    ChatRoomReadResponse,
    ChatRoomStateResponse,
    ChatRoomUnreadCountResponse,
    ChatRoomUnreadSummaryResponse,
)
from app.services.chat_room_service import (
    get_room_state,
    get_room_unread_count,
    get_unread_summary,
    mark_room_as_read,
    set_room_muted,
)
from app.utils.enums import ChatRoomType


router = APIRouter(prefix="/chat-rooms", tags=["ChatRooms"])


@router.get("/state", response_model=ChatRoomStateResponse)
def get_chat_room_state(
    room_type: ChatRoomType,
    room_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> ChatRoomStateResponse:
    return get_room_state(
        db,
        current_user=current_user,
        room_type=room_type,
        room_id=room_id,
    )


@router.post("/read", response_model=ChatRoomReadResponse)
def mark_chat_room_read(
    payload: ChatRoomReadRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> ChatRoomReadResponse:
    return mark_room_as_read(
        db,
        current_user=current_user,
        room_type=payload.room_type,
        room_id=payload.room_id,
        last_read_message_id=payload.last_read_message_id,
    )


@router.get("/unread-count", response_model=ChatRoomUnreadCountResponse)
def get_chat_room_unread_count(
    room_type: ChatRoomType,
    room_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> ChatRoomUnreadCountResponse:
    return get_room_unread_count(
        db,
        current_user=current_user,
        room_type=room_type,
        room_id=room_id,
    )


@router.get("/unread-summary", response_model=ChatRoomUnreadSummaryResponse)
def get_chat_room_unread_summary(
    db: DBSession,
    current_user: CurrentUser,
) -> ChatRoomUnreadSummaryResponse:
    return get_unread_summary(db, current_user=current_user)


@router.put("/mute", response_model=ChatRoomMuteResponse)
def mute_chat_room(
    payload: ChatRoomMuteRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> ChatRoomMuteResponse:
    return set_room_muted(
        db,
        current_user=current_user,
        room_type=payload.room_type,
        room_id=payload.room_id,
        is_muted=True,
    )


@router.delete("/mute", response_model=ChatRoomMuteResponse)
def unmute_chat_room(
    db: DBSession,
    current_user: CurrentUser,
    room_type: ChatRoomType = Query(...),
    room_id: UUID = Query(...),
) -> ChatRoomMuteResponse:
    return set_room_muted(
        db,
        current_user=current_user,
        room_type=room_type,
        room_id=room_id,
        is_muted=False,
    )
