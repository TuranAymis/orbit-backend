from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DBSession
from app.crud import chat as chat_crud
from app.schemas.chat import ChatCreate, ChatRead
from app.services.chat_service import persist_chat_message, resolve_chat_context, to_chat_read


router = APIRouter(prefix="/chats", tags=["Chats"])


@router.post("", response_model=ChatRead, status_code=status.HTTP_201_CREATED)
def create_chat(
    payload: ChatCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> ChatRead:
    resolved_group_id, resolved_event_id = resolve_chat_context(
        db,
        current_user=current_user,
        group_id=payload.group_id,
        event_id=payload.event_id,
    )
    return persist_chat_message(
        db,
        current_user=current_user,
        group_id=resolved_group_id,
        event_id=resolved_event_id,
        content=payload.content,
    )


@router.get("", response_model=list[ChatRead])
def list_chats(
    db: DBSession,
    current_user: CurrentUser,
    group_id: UUID | None = Query(default=None),
    event_id: UUID | None = Query(default=None),
    limit: int = Query(100, ge=1, le=200),
) -> list[ChatRead]:
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
