from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException, AuthorizationError
from app.crud import chat as chat_crud
from app.crud import chat_room_state as chat_room_state_crud
from app.crud import event as event_crud
from app.crud import group as group_crud
from app.crud import membership as membership_crud
from app.crud import notification as notification_crud
from app.models.chat import Chat
from app.models.chat_room_state import ChatRoomState
from app.models.event import Event
from app.models.group import Group
from app.models.membership import Membership
from app.models.notification import Notification
from app.models.user import User
from app.schemas.chat_room import (
    ChatRoomMuteResponse,
    ChatRoomReadResponse,
    ChatRoomStateResponse,
    ChatRoomUnreadCountResponse,
    ChatRoomUnreadSummaryItem,
    ChatRoomUnreadSummaryResponse,
)
from app.utils.enums import ChatRoomType, MembershipStatus


CHAT_NOTIFICATION_TYPE = "chat_message"


@dataclass(slots=True)
class ResolvedChatRoom:
    room_type: ChatRoomType
    room_id: uuid.UUID
    group_id: uuid.UUID | None
    event_id: uuid.UUID | None


def _related_entity_type_for_room(room_type: ChatRoomType) -> str:
    return f"{room_type.value}_chat"


def resolve_chat_room(
    db: Session,
    *,
    current_user: User,
    room_type: ChatRoomType,
    room_id: uuid.UUID,
) -> ResolvedChatRoom:
    resolved_group_id = room_id if room_type == ChatRoomType.GROUP else None
    resolved_event_id = room_id if room_type == ChatRoomType.EVENT else None

    if resolved_event_id is not None:
        event = event_crud.get_event(db, resolved_event_id)
        resolved_group_id = event.group_id

    if resolved_group_id is not None:
        group = group_crud.get_group(db, resolved_group_id)
        if group.owner_id != current_user.id:
            membership = membership_crud.get_membership_by_user_group(
                db,
                user_id=current_user.id,
                group_id=resolved_group_id,
            )
            if membership is None or membership.status != MembershipStatus.ACTIVE:
                raise AuthorizationError("Only active group members can access this chat.")

    if room_type == ChatRoomType.GROUP:
        return ResolvedChatRoom(
            room_type=room_type,
            room_id=resolved_group_id,
            group_id=resolved_group_id,
            event_id=None,
        )

    if room_type == ChatRoomType.EVENT:
        return ResolvedChatRoom(
            room_type=room_type,
            room_id=resolved_event_id,
            group_id=resolved_group_id,
            event_id=resolved_event_id,
        )

    raise AppException("Unsupported room type.")


def _list_accessible_group_ids(db: Session, *, user_id: uuid.UUID) -> list[uuid.UUID]:
    owner_stmt = select(Group.id).where(Group.owner_id == user_id)
    member_stmt = select(Membership.group_id).where(
        Membership.user_id == user_id,
        Membership.status == MembershipStatus.ACTIVE,
    )
    union_subquery = owner_stmt.union(member_stmt).subquery()
    stmt = select(union_subquery.c[0])
    return list(db.scalars(stmt).all())


def _list_accessible_event_ids(
    db: Session,
    *,
    accessible_group_ids: list[uuid.UUID],
) -> list[uuid.UUID]:
    if not accessible_group_ids:
        return []

    stmt = select(Event.id).where(Event.group_id.in_(accessible_group_ids))
    return list(db.scalars(stmt).all())


def _get_room_filter(room_type: ChatRoomType, room_id: uuid.UUID):
    if room_type == ChatRoomType.GROUP:
        return Chat.group_id == room_id
    return Chat.event_id == room_id


def _apply_unread_boundary(
    stmt,
    *,
    user_id: uuid.UUID,
    room_type: ChatRoomType,
    room_id: uuid.UUID,
    state: ChatRoomState | None,
):
    stmt = stmt.where(_get_room_filter(room_type, room_id), Chat.sender_id != user_id)

    if state is None or state.last_read_at is None:
        return stmt

    if state.last_read_message_id is not None:
        return stmt.where(
            or_(
                Chat.created_at > state.last_read_at,
                and_(Chat.created_at == state.last_read_at, Chat.id > state.last_read_message_id),
            )
        )

    return stmt.where(Chat.created_at > state.last_read_at)


def count_unread_for_room(
    db: Session,
    *,
    current_user: User,
    room_type: ChatRoomType,
    room_id: uuid.UUID,
    state: ChatRoomState | None = None,
) -> int:
    effective_state = state or chat_room_state_crud.get_chat_room_state(
        db,
        user_id=current_user.id,
        room_type=room_type,
        room_id=room_id,
    )
    stmt = select(func.count(Chat.id)).select_from(Chat)
    stmt = _apply_unread_boundary(
        stmt,
        user_id=current_user.id,
        room_type=room_type,
        room_id=room_id,
        state=effective_state,
    )
    return int(db.scalar(stmt) or 0)


def get_room_state(
    db: Session,
    *,
    current_user: User,
    room_type: ChatRoomType,
    room_id: uuid.UUID,
) -> ChatRoomStateResponse:
    resolved_room = resolve_chat_room(
        db,
        current_user=current_user,
        room_type=room_type,
        room_id=room_id,
    )
    state = chat_room_state_crud.get_chat_room_state(
        db,
        user_id=current_user.id,
        room_type=resolved_room.room_type,
        room_id=resolved_room.room_id,
    )
    return ChatRoomStateResponse(
        room_type=resolved_room.room_type,
        room_id=resolved_room.room_id,
        is_muted=state.is_muted if state is not None else False,
        last_read_message_id=state.last_read_message_id if state is not None else None,
        last_read_at=state.last_read_at if state is not None else None,
        unread_count=count_unread_for_room(
            db,
            current_user=current_user,
            room_type=resolved_room.room_type,
            room_id=resolved_room.room_id,
            state=state,
        ),
    )


def mark_room_as_read(
    db: Session,
    *,
    current_user: User,
    room_type: ChatRoomType,
    room_id: uuid.UUID,
    last_read_message_id: uuid.UUID | None,
) -> ChatRoomReadResponse:
    resolved_room = resolve_chat_room(
        db,
        current_user=current_user,
        room_type=room_type,
        room_id=room_id,
    )

    last_read_message = None
    if last_read_message_id is not None:
        last_read_message = chat_crud.get_chat(db, chat_id=last_read_message_id)
        if last_read_message is None:
            raise AppException("last_read_message_id does not exist.")
        if resolved_room.room_type == ChatRoomType.GROUP and last_read_message.group_id != resolved_room.room_id:
            raise AppException("last_read_message_id does not belong to this room.")
        if resolved_room.room_type == ChatRoomType.EVENT and last_read_message.event_id != resolved_room.room_id:
            raise AppException("last_read_message_id does not belong to this room.")
    else:
        last_read_message = chat_crud.get_latest_chat_for_room(
            db,
            group_id=resolved_room.group_id,
            event_id=resolved_room.event_id,
        )

    state = chat_room_state_crud.upsert_read_marker(
        db,
        user_id=current_user.id,
        room_type=resolved_room.room_type,
        room_id=resolved_room.room_id,
        last_read_message_id=last_read_message.id if last_read_message is not None else None,
        last_read_at=last_read_message.created_at if last_read_message is not None else None,
    )

    notification_crud.mark_notifications_as_read_for_entity(
        db,
        user_id=current_user.id,
        type=CHAT_NOTIFICATION_TYPE,
        related_entity_type=_related_entity_type_for_room(resolved_room.room_type),
        related_entity_id=resolved_room.room_id,
    )

    return ChatRoomReadResponse(
        room_type=resolved_room.room_type,
        room_id=resolved_room.room_id,
        is_muted=state.is_muted,
        last_read_message_id=state.last_read_message_id,
        last_read_at=state.last_read_at,
        unread_count=count_unread_for_room(
            db,
            current_user=current_user,
            room_type=resolved_room.room_type,
            room_id=resolved_room.room_id,
            state=state,
        ),
    )


def set_room_muted(
    db: Session,
    *,
    current_user: User,
    room_type: ChatRoomType,
    room_id: uuid.UUID,
    is_muted: bool,
) -> ChatRoomMuteResponse:
    resolved_room = resolve_chat_room(
        db,
        current_user=current_user,
        room_type=room_type,
        room_id=room_id,
    )
    state = chat_room_state_crud.set_room_muted(
        db,
        user_id=current_user.id,
        room_type=resolved_room.room_type,
        room_id=resolved_room.room_id,
        is_muted=is_muted,
    )
    return ChatRoomMuteResponse(
        room_type=resolved_room.room_type,
        room_id=resolved_room.room_id,
        is_muted=state.is_muted,
    )


def get_room_unread_count(
    db: Session,
    *,
    current_user: User,
    room_type: ChatRoomType,
    room_id: uuid.UUID,
) -> ChatRoomUnreadCountResponse:
    resolved_room = resolve_chat_room(
        db,
        current_user=current_user,
        room_type=room_type,
        room_id=room_id,
    )
    state = chat_room_state_crud.get_chat_room_state(
        db,
        user_id=current_user.id,
        room_type=resolved_room.room_type,
        room_id=resolved_room.room_id,
    )
    return ChatRoomUnreadCountResponse(
        room_type=resolved_room.room_type,
        room_id=resolved_room.room_id,
        unread_count=count_unread_for_room(
            db,
            current_user=current_user,
            room_type=resolved_room.room_type,
            room_id=resolved_room.room_id,
            state=state,
        ),
        is_muted=state.is_muted if state is not None else False,
    )


def _count_unread_for_rooms(
    db: Session,
    *,
    current_user: User,
    room_type: ChatRoomType,
    accessible_room_ids: list[uuid.UUID],
) -> dict[uuid.UUID, int]:
    if not accessible_room_ids:
        return {}

    state_subquery = (
        select(
            ChatRoomState.room_id.label("room_id"),
            ChatRoomState.last_read_at.label("last_read_at"),
            ChatRoomState.last_read_message_id.label("last_read_message_id"),
        )
        .where(
            ChatRoomState.user_id == current_user.id,
            ChatRoomState.room_type == room_type.value,
            ChatRoomState.room_id.in_(accessible_room_ids),
        )
        .subquery()
    )

    room_column = Chat.group_id if room_type == ChatRoomType.GROUP else Chat.event_id
    unread_boundary = or_(
        state_subquery.c.room_id.is_(None),
        state_subquery.c.last_read_at.is_(None),
        Chat.created_at > state_subquery.c.last_read_at,
        and_(
            state_subquery.c.last_read_message_id.is_not(None),
            Chat.created_at == state_subquery.c.last_read_at,
            Chat.id > state_subquery.c.last_read_message_id,
        ),
    )

    stmt = (
        select(room_column, func.count(Chat.id))
        .select_from(Chat)
        .outerjoin(state_subquery, state_subquery.c.room_id == room_column)
        .where(
            room_column.in_(accessible_room_ids),
            Chat.sender_id != current_user.id,
            unread_boundary,
        )
        .group_by(room_column)
    )
    return {room_id: int(count) for room_id, count in db.execute(stmt).all()}


def get_unread_summary(
    db: Session,
    *,
    current_user: User,
) -> ChatRoomUnreadSummaryResponse:
    accessible_group_ids = _list_accessible_group_ids(db, user_id=current_user.id)
    accessible_event_ids = _list_accessible_event_ids(
        db,
        accessible_group_ids=accessible_group_ids,
    )

    group_counts = _count_unread_for_rooms(
        db,
        current_user=current_user,
        room_type=ChatRoomType.GROUP,
        accessible_room_ids=accessible_group_ids,
    )
    event_counts = _count_unread_for_rooms(
        db,
        current_user=current_user,
        room_type=ChatRoomType.EVENT,
        accessible_room_ids=accessible_event_ids,
    )

    states = chat_room_state_crud.list_chat_room_states_by_user(db, user_id=current_user.id)
    items_by_key: dict[tuple[ChatRoomType, uuid.UUID], ChatRoomUnreadSummaryItem] = {}

    for room_id, unread_count in group_counts.items():
        items_by_key[(ChatRoomType.GROUP, room_id)] = ChatRoomUnreadSummaryItem(
            room_type=ChatRoomType.GROUP,
            room_id=room_id,
            unread_count=unread_count,
            is_muted=False,
        )

    for room_id, unread_count in event_counts.items():
        items_by_key[(ChatRoomType.EVENT, room_id)] = ChatRoomUnreadSummaryItem(
            room_type=ChatRoomType.EVENT,
            room_id=room_id,
            unread_count=unread_count,
            is_muted=False,
        )

    accessible_group_id_set = set(accessible_group_ids)
    accessible_event_id_set = set(accessible_event_ids)
    for state in states:
        if state.room_type == ChatRoomType.GROUP and state.room_id not in accessible_group_id_set:
            continue
        if state.room_type == ChatRoomType.EVENT and state.room_id not in accessible_event_id_set:
            continue

        key = (state.room_type, state.room_id)
        existing_item = items_by_key.get(key)
        if existing_item is None:
            items_by_key[key] = ChatRoomUnreadSummaryItem(
                room_type=state.room_type,
                room_id=state.room_id,
                unread_count=0,
                is_muted=state.is_muted,
            )
        else:
            existing_item.is_muted = state.is_muted

    items = sorted(
        items_by_key.values(),
        key=lambda item: (item.unread_count, str(item.room_id)),
        reverse=True,
    )
    return ChatRoomUnreadSummaryResponse(
        total_unread_count=sum(item.unread_count for item in items),
        rooms=items,
    )


def sync_sender_read_state_for_message(
    db: Session,
    *,
    sender_id: uuid.UUID,
    group_id: uuid.UUID | None,
    event_id: uuid.UUID | None,
    message_id: uuid.UUID,
    created_at,
) -> ChatRoomState:
    room_type = ChatRoomType.EVENT if event_id is not None else ChatRoomType.GROUP
    room_id = event_id or group_id
    return chat_room_state_crud.upsert_read_marker(
        db,
        user_id=sender_id,
        room_type=room_type,
        room_id=room_id,
        last_read_message_id=message_id,
        last_read_at=created_at,
    )


def get_notification_eligible_user_ids_for_message(
    db: Session,
    *,
    room_type: ChatRoomType,
    room_id: uuid.UUID,
    sender_id: uuid.UUID,
) -> list[uuid.UUID]:
    if room_type == ChatRoomType.GROUP:
        group = db.get(Group, room_id)
        if group is None:
            return []
        candidate_ids = {group.owner_id}
        membership_stmt = select(Membership.user_id).where(
            Membership.group_id == room_id,
            Membership.status == MembershipStatus.ACTIVE,
        )
        candidate_ids.update(db.scalars(membership_stmt).all())
    else:
        event = db.get(Event, room_id)
        if event is None:
            return []
        group = db.get(Group, event.group_id)
        if group is None:
            return []
        candidate_ids = {group.owner_id}
        membership_stmt = select(Membership.user_id).where(
            Membership.group_id == event.group_id,
            Membership.status == MembershipStatus.ACTIVE,
        )
        candidate_ids.update(db.scalars(membership_stmt).all())

    candidate_ids.discard(sender_id)
    if not candidate_ids:
        return []

    muted_stmt = select(ChatRoomState.user_id).where(
        ChatRoomState.room_type == room_type.value,
        ChatRoomState.room_id == room_id,
        ChatRoomState.is_muted.is_(True),
        ChatRoomState.user_id.in_(candidate_ids),
    )
    muted_user_ids = set(db.scalars(muted_stmt).all())
    return sorted(candidate_ids - muted_user_ids, key=str)


def create_notifications_for_chat_message(
    db: Session,
    *,
    chat: Chat,
) -> int:
    room_type = ChatRoomType.EVENT if chat.event_id is not None else ChatRoomType.GROUP
    room_id = chat.event_id or chat.group_id
    if room_id is None:
        return 0

    eligible_user_ids = get_notification_eligible_user_ids_for_message(
        db,
        room_type=room_type,
        room_id=room_id,
        sender_id=chat.sender_id,
    )
    if not eligible_user_ids:
        return 0

    if room_type == ChatRoomType.EVENT:
        room = db.get(Event, room_id)
        room_name = room.title if room is not None else "an event chat"
    else:
        room = db.get(Group, room_id)
        room_name = room.name if room is not None else "a group chat"

    preview = chat.message if len(chat.message) <= 160 else f"{chat.message[:157]}..."
    payloads = [
        {
            "user_id": user_id,
            "type": CHAT_NOTIFICATION_TYPE,
            "title": f"New message in {room_name}",
            "message": f"{chat.sender.full_name}: {preview}",
            "is_read": False,
            "related_entity_type": _related_entity_type_for_room(room_type),
            "related_entity_id": room_id,
        }
        for user_id in eligible_user_ids
    ]
    notification_crud.create_notifications_batch(db, payloads=payloads)
    return len(payloads)
