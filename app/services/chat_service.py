from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import AuthorizationError
from app.crud import chat as chat_crud
from app.crud import event as event_crud
from app.crud import group as group_crud
from app.crud import membership as membership_crud
from app.models.user import User
from app.schemas.chat import ChatRead
from app.services.chat_room_service import (
    create_notifications_for_chat_message,
    sync_sender_read_state_for_message,
)
from app.utils.enums import MembershipStatus


def to_chat_read(chat) -> ChatRead:
    return ChatRead(
        id=chat.id,
        group_id=chat.group_id,
        event_id=chat.event_id,
        user_id=chat.sender_id,
        username=chat.sender.full_name,
        content=chat.message,
        created_at=chat.created_at,
    )


def resolve_chat_context(
    db: Session,
    *,
    current_user: User,
    group_id: UUID | None,
    event_id: UUID | None,
) -> tuple[UUID | None, UUID | None]:
    resolved_group_id = group_id
    resolved_event_id = event_id

    if event_id is not None:
        event = event_crud.get_event(db, event_id)
        if group_id is not None and event.group_id != group_id:
            raise AuthorizationError("event_id does not belong to the provided group_id.")
        resolved_group_id = event.group_id

    if resolved_group_id is not None:
        group = group_crud.get_group(db, resolved_group_id)
        if group.owner_id == current_user.id:
            return resolved_group_id, resolved_event_id

        membership = membership_crud.get_membership_by_user_group(
            db,
            user_id=current_user.id,
            group_id=resolved_group_id,
        )
        if membership is None or membership.status != MembershipStatus.ACTIVE:
            raise AuthorizationError("Only active group members can access this chat.")

    return resolved_group_id, resolved_event_id


def build_room_name(*, group_id: UUID | None, event_id: UUID | None) -> str:
    if event_id is not None:
        return f"event:{event_id}"
    if group_id is not None:
        return f"group:{group_id}"
    raise ValueError("Either group_id or event_id must be provided.")


def persist_chat_message(
    db: Session,
    *,
    current_user: User,
    group_id: UUID | None,
    event_id: UUID | None,
    content: str,
) -> ChatRead:
    chat = chat_crud.create_chat(
        db,
        sender_id=current_user.id,
        group_id=group_id,
        event_id=event_id,
        message=content,
    )
    chat = chat_crud.get_chat(db, chat_id=chat.id)
    sync_sender_read_state_for_message(
        db,
        sender_id=current_user.id,
        group_id=chat.group_id,
        event_id=chat.event_id,
        message_id=chat.id,
        created_at=chat.created_at,
    )
    create_notifications_for_chat_message(db, chat=chat)
    return to_chat_read(chat)
