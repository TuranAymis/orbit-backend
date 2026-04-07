import uuid
from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.chat import Chat


def create_chat(
    db: Session,
    *,
    sender_id: uuid.UUID,
    group_id: uuid.UUID | None,
    event_id: uuid.UUID | None,
    message: str,
) -> Chat:
    chat = Chat(
        sender_id=sender_id,
        group_id=group_id,
        event_id=event_id,
        message=message.strip(),
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


def list_chats(
    db: Session,
    *,
    group_id: uuid.UUID | None = None,
    event_id: uuid.UUID | None = None,
    sender_id: uuid.UUID | None = None,
    limit: int = 100,
) -> list[Chat]:
    stmt = select(Chat)
    if group_id is not None:
        stmt = stmt.where(Chat.group_id == group_id)
    if event_id is not None:
        stmt = stmt.where(Chat.event_id == event_id)
    if sender_id is not None:
        stmt = stmt.where(Chat.sender_id == sender_id)

    stmt = stmt.order_by(Chat.created_at.asc(), Chat.id.asc()).limit(limit)
    return list(db.scalars(stmt).all())


def get_chat_by_context_and_message(
    db: Session,
    *,
    sender_id: uuid.UUID,
    group_id: uuid.UUID | None,
    event_id: uuid.UUID | None,
    message: str,
) -> Chat | None:
    stmt = select(Chat).where(
        Chat.sender_id == sender_id,
        Chat.group_id == group_id,
        Chat.event_id == event_id,
        Chat.message == message.strip(),
    )
    return db.scalar(stmt)


def get_chat(db: Session, *, chat_id: uuid.UUID) -> Chat | None:
    return db.get(Chat, chat_id)


def get_latest_chat_for_room(
    db: Session,
    *,
    group_id: uuid.UUID | None = None,
    event_id: uuid.UUID | None = None,
) -> Chat | None:
    stmt = select(Chat)
    if group_id is not None:
        stmt = stmt.where(Chat.group_id == group_id)
    if event_id is not None:
        stmt = stmt.where(Chat.event_id == event_id)
    stmt = stmt.order_by(Chat.created_at.desc(), Chat.id.desc()).limit(1)
    return db.scalar(stmt)


def list_chats_since(
    db: Session,
    *,
    group_id: uuid.UUID | None = None,
    event_id: uuid.UUID | None = None,
    after_chat_id: uuid.UUID | None = None,
    after_created_at: datetime | None = None,
    limit: int = 200,
) -> list[Chat]:
    stmt = select(Chat)
    if group_id is not None:
        stmt = stmt.where(Chat.group_id == group_id)
    if event_id is not None:
        stmt = stmt.where(Chat.event_id == event_id)

    cursor_chat = get_chat(db, chat_id=after_chat_id) if after_chat_id is not None else None
    effective_created_at = after_created_at or (cursor_chat.created_at if cursor_chat else None)

    if effective_created_at is not None:
        if cursor_chat is not None:
            stmt = stmt.where(
                or_(
                    Chat.created_at > effective_created_at,
                    and_(Chat.created_at == effective_created_at, Chat.id > cursor_chat.id),
                )
            )
        else:
            stmt = stmt.where(Chat.created_at > effective_created_at)

    stmt = stmt.order_by(Chat.created_at.asc(), Chat.id.asc()).limit(limit)
    return list(db.scalars(stmt).all())
