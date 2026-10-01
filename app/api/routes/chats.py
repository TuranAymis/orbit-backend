from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from app.api.deps import CurrentUser, DBSession
from app.crud import chat as chat_crud
from app.schemas.chat import ChatCreate, ChatRead
from app.services.chat_service import build_room_name, persist_chat_message, resolve_chat_context, to_chat_read
from app.services.chat_realtime import chat_connection_manager


router = APIRouter(prefix="/chats", tags=["Chats"])


@router.post("", response_model=ChatRead, status_code=status.HTTP_201_CREATED)
def create_chat(
    payload: ChatCreate,
    background_tasks: BackgroundTasks,
    db: DBSession,
    current_user: CurrentUser,
) -> ChatRead:
    resolved_group_id, resolved_event_id = resolve_chat_context(
        db,
        current_user=current_user,
        group_id=payload.group_id,
        event_id=payload.event_id,
    )
    message = persist_chat_message(
        db,
        current_user=current_user,
        group_id=resolved_group_id,
        event_id=resolved_event_id,
        content=payload.content,
    )
    background_tasks.add_task(chat_connection_manager.broadcast,
        room_name=build_room_name(group_id=message.group_id, event_id=message.event_id),
        event="chat:message", data=message.model_dump(mode="json"))
    return message


@router.get("", response_model=list[ChatRead])
def list_chats(
    db: DBSession,
    current_user: CurrentUser,
    group_id: UUID | None = Query(default=None),
    event_id: UUID | None = Query(default=None),
    limit: int = Query(100, ge=1, le=200),
    after_id: UUID | None = Query(default=None),
) -> list[ChatRead]:
    if after_id is not None:
        resolved_group_id, resolved_event_id = resolve_chat_context(
            db, current_user=current_user, group_id=group_id, event_id=event_id,
        )
        cursor = chat_crud.get_chat(db, chat_id=after_id)
        if cursor is None or cursor.group_id != resolved_group_id or cursor.event_id != resolved_event_id:
            raise HTTPException(status_code=400, detail="Invalid chat cursor.")
        return [to_chat_read(chat) for chat in chat_crud.list_chats_since(
            db, group_id=resolved_group_id, event_id=resolved_event_id,
            after_chat_id=after_id, limit=limit,
        )]
    if group_id is None and event_id is None:
        chats = chat_crud.list_chats(db, sender_id=current_user.id, limit=limit)
        return [to_chat_read(chat) for chat in chats]

    resolved_group_id, resolved_event_id = resolve_chat_context(
        db,
        current_user=current_user,
        group_id=group_id,
        event_id=event_id,
    )
    chats = chat_crud.list_chats(
        db,
        group_id=resolved_group_id,
        event_id=resolved_event_id,
        limit=limit,
    )
    return [to_chat_read(chat) for chat in chats]
