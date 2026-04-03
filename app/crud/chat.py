import uuid

from sqlalchemy import select
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
