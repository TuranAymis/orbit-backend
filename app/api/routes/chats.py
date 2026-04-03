from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, DBSession
from app.core.exceptions import AuthorizationError
from app.crud import chat as chat_crud
from app.crud import event as event_crud
from app.crud import group as group_crud
from app.crud import membership as membership_crud
from app.models.user import User
from app.schemas.chat import ChatCreate, ChatRead
from app.utils.enums import MembershipStatus


router = APIRouter(prefix="/chats", tags=["Chats"])


def _resolve_chat_context(
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
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="event_id does not belong to the provided group_id.",
            )
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


@router.post("", response_model=ChatRead, status_code=status.HTTP_201_CREATED)
def create_chat(
    payload: ChatCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> ChatRead:
    message = payload.message.strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message cannot be empty.",
        )

    resolved_group_id, resolved_event_id = _resolve_chat_context(
        db,
        current_user=current_user,
        group_id=payload.group_id,
        event_id=payload.event_id,
    )
    return chat_crud.create_chat(
        db,
        sender_id=current_user.id,
        group_id=resolved_group_id,
        event_id=resolved_event_id,
        message=message,
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
        return chat_crud.list_chats(db, sender_id=current_user.id, limit=limit)

    resolved_group_id, resolved_event_id = _resolve_chat_context(
        db,
        current_user=current_user,
        group_id=group_id,
        event_id=event_id,
    )
    return chat_crud.list_chats(
        db,
        group_id=resolved_group_id,
        event_id=resolved_event_id,
        limit=limit,
    )
