import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.chat_room_state import ChatRoomState
from app.utils.enums import ChatRoomType


def get_chat_room_state(
    db: Session,
    *,
    user_id: uuid.UUID,
    room_type: ChatRoomType,
    room_id: uuid.UUID,
) -> ChatRoomState | None:
    stmt = select(ChatRoomState).where(
        ChatRoomState.user_id == user_id,
        ChatRoomState.room_type == room_type.value,
        ChatRoomState.room_id == room_id,
    )
    return db.scalar(stmt)


def list_chat_room_states_by_user(
    db: Session,
    *,
    user_id: uuid.UUID,
    room_type: ChatRoomType | None = None,
) -> list[ChatRoomState]:
    stmt = select(ChatRoomState).where(ChatRoomState.user_id == user_id)
    if room_type is not None:
        stmt = stmt.where(ChatRoomState.room_type == room_type.value)
    stmt = stmt.order_by(ChatRoomState.updated_at.desc(), ChatRoomState.id.desc())
    return list(db.scalars(stmt).all())


def ensure_chat_room_state(
    db: Session,
    *,
    user_id: uuid.UUID,
    room_type: ChatRoomType,
    room_id: uuid.UUID,
) -> ChatRoomState:
    state = get_chat_room_state(db, user_id=user_id, room_type=room_type, room_id=room_id)
    if state is not None:
        return state

    state = ChatRoomState(
        user_id=user_id,
        room_type=room_type.value,
        room_id=room_id,
    )
    db.add(state)
    db.commit()
    db.refresh(state)
    return state


def upsert_read_marker(
    db: Session,
    *,
    user_id: uuid.UUID,
    room_type: ChatRoomType,
    room_id: uuid.UUID,
    last_read_message_id: uuid.UUID | None,
    last_read_at: datetime | None,
) -> ChatRoomState:
    state = ensure_chat_room_state(
        db,
        user_id=user_id,
        room_type=room_type,
        room_id=room_id,
    )
    state.last_read_message_id = last_read_message_id
    state.last_read_at = last_read_at
    db.add(state)
    db.commit()
    db.refresh(state)
    return state


def set_room_muted(
    db: Session,
    *,
    user_id: uuid.UUID,
    room_type: ChatRoomType,
    room_id: uuid.UUID,
    is_muted: bool,
) -> ChatRoomState:
    state = ensure_chat_room_state(
        db,
        user_id=user_id,
        room_type=room_type,
        room_id=room_id,
    )
    state.is_muted = is_muted
    if not is_muted:
        state.muted_until = None
    db.add(state)
    db.commit()
    db.refresh(state)
    return state


def delete_chat_room_states_for_room(
    db: Session,
    *,
    room_type: ChatRoomType,
    room_id: uuid.UUID,
) -> None:
    db.execute(
        delete(ChatRoomState).where(
            ChatRoomState.room_type == room_type.value,
            ChatRoomState.room_id == room_id,
        )
    )
    db.commit()
