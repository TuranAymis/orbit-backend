from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession
from app.crud import notification as notification_crud
from app.schemas.notification import (
    NotificationMarkReadResponse,
    NotificationRead,
    NotificationUnreadCountResponse,
)


router = APIRouter(prefix="/notifications", tags=["Notifications"])


def _to_notification_read(notification) -> NotificationRead:
    return NotificationRead(
        id=notification.id,
        type=notification.type,
        title=notification.title,
        message=notification.message,
        created_at=notification.created_at,
        is_read=notification.is_read,
        related_entity_type=notification.related_entity_type,
        related_entity_id=notification.related_entity_id,
    )


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    db: DBSession,
    current_user: CurrentUser,
    limit: int = Query(100, ge=1, le=200),
) -> list[NotificationRead]:
    notifications = notification_crud.list_notifications_by_user(
        db,
        user_id=current_user.id,
        limit=limit,
    )
    return [_to_notification_read(notification) for notification in notifications]


@router.get("/unread-count", response_model=NotificationUnreadCountResponse)
def get_unread_count(
    db: DBSession,
    current_user: CurrentUser,
) -> NotificationUnreadCountResponse:
    return NotificationUnreadCountResponse(
        count=notification_crud.count_unread_notifications_by_user(
            db,
            user_id=current_user.id,
        )
    )


@router.post("/{notification_id}/read", response_model=NotificationMarkReadResponse)
def mark_notification_read(
    notification_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> NotificationMarkReadResponse:
    notification = notification_crud.get_notification_for_user(
        db,
        notification_id=notification_id,
        user_id=current_user.id,
    )
    notification_crud.mark_notification_as_read(db, notification=notification)
    return NotificationMarkReadResponse(success=True)
