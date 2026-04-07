import uuid

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundError
from app.models.notification import Notification


def create_notification(
    db: Session,
    *,
    user_id: uuid.UUID,
    type: str,
    title: str,
    message: str,
    is_read: bool = False,
    related_entity_type: str | None = None,
    related_entity_id: uuid.UUID | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        type=type.strip(),
        title=title.strip(),
        message=message.strip(),
        is_read=is_read,
        related_entity_type=related_entity_type.strip() if related_entity_type else None,
        related_entity_id=related_entity_id,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def list_notifications_by_user(
    db: Session,
    *,
    user_id: uuid.UUID,
    limit: int = 100,
) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def count_unread_notifications_by_user(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> int:
    stmt = select(func.count()).select_from(Notification).where(
        Notification.user_id == user_id,
        Notification.is_read.is_(False),
    )
    return int(db.scalar(stmt) or 0)


def get_notification_for_user(
    db: Session,
    *,
    notification_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Notification:
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    )
    notification = db.scalar(stmt)
    if notification is None:
        raise ResourceNotFoundError("Notification not found.")
    return notification


def mark_notification_as_read(
    db: Session,
    *,
    notification: Notification,
) -> Notification:
    if notification.is_read:
        return notification

    notification.is_read = True
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def get_notification_by_signature(
    db: Session,
    *,
    user_id: uuid.UUID,
    type: str,
    title: str,
    message: str,
) -> Notification | None:
    stmt = select(Notification).where(
        Notification.user_id == user_id,
        Notification.type == type.strip(),
        Notification.title == title.strip(),
        Notification.message == message.strip(),
    )
    return db.scalar(stmt)


def create_notifications_batch(
    db: Session,
    *,
    payloads: list[dict],
) -> list[Notification]:
    if not payloads:
        return []

    notifications = [Notification(**payload) for payload in payloads]
    db.add_all(notifications)
    db.commit()
    for notification in notifications:
        db.refresh(notification)
    return notifications


def mark_notifications_as_read_for_entity(
    db: Session,
    *,
    user_id: uuid.UUID,
    type: str,
    related_entity_type: str,
    related_entity_id: uuid.UUID,
) -> int:
    stmt = (
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.type == type.strip(),
            Notification.related_entity_type == related_entity_type.strip(),
            Notification.related_entity_id == related_entity_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    result = db.execute(stmt)
    db.commit()
    return int(result.rowcount or 0)
