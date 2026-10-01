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

from fastapi import BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from app.models.push import NotificationPreference, PushSubscription
from app.core.config import settings

CATEGORIES = ("chat", "event", "group")

class PreferenceUpdate(BaseModel):
    enabled: bool

class SubscriptionKeys(BaseModel):
    p256dh: str = Field(min_length=1)
    auth: str = Field(min_length=1)

class SubscriptionCreate(BaseModel):
    endpoint: str = Field(min_length=8, max_length=4096)
    keys: SubscriptionKeys

@router.get("/preferences")
def list_preferences(db: DBSession, current_user: CurrentUser) -> dict[str, bool]:
    stored = db.scalars(select(NotificationPreference).where(NotificationPreference.user_id == current_user.id)).all()
    values = {item.category: item.enabled for item in stored}
    return {category: values.get(category, True) for category in CATEGORIES}

@router.put("/preferences/{category}")
def update_preference(category: str, payload: PreferenceUpdate, db: DBSession, current_user: CurrentUser) -> dict:
    if category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Unknown notification category")
    preference = db.get(NotificationPreference, (current_user.id, category))
    if preference is None:
        preference = NotificationPreference(user_id=current_user.id, category=category)
        db.add(preference)
    preference.enabled = payload.enabled
    db.commit()
    return {"category": category, "enabled": preference.enabled}

@router.get("/push/config")
def push_config() -> dict:
    return {"public_key": settings.VAPID_PUBLIC_KEY}

@router.post("/push/subscriptions", status_code=201)
def register_subscription(payload: SubscriptionCreate, request: Request, db: DBSession, current_user: CurrentUser) -> dict:
    if not payload.endpoint.startswith("https://"):
        raise HTTPException(status_code=422, detail="Push endpoint must use HTTPS")
    subscription = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == payload.endpoint))
    if subscription is not None and subscription.user_id != current_user.id:
        raise HTTPException(status_code=409, detail="Subscription already registered")
    if subscription is None:
        subscription = PushSubscription(user_id=current_user.id, endpoint=payload.endpoint)
        db.add(subscription)
    subscription.p256dh = payload.keys.p256dh
    subscription.auth = payload.keys.auth
    subscription.user_agent = request.headers.get("user-agent", "")[:512]
    db.commit()
    return {"id": subscription.id, "endpoint": subscription.endpoint}

class SubscriptionDelete(BaseModel):
    endpoint: str

@router.delete("/push/subscriptions", status_code=204)
def delete_subscription(payload: SubscriptionDelete, db: DBSession, current_user: CurrentUser) -> None:
    subscription = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == payload.endpoint,
                                                             PushSubscription.user_id == current_user.id))
    if subscription is not None:
        db.delete(subscription)
        db.commit()
