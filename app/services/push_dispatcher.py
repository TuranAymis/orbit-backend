import json
import logging
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.push import NotificationPreference, PushSubscription

logger = logging.getLogger(__name__)


class PushSender(Protocol):
    def send(self, subscription: PushSubscription, payload: dict) -> None: ...


class LoggingPushSender:
    def send(self, subscription: PushSubscription, payload: dict) -> None:
        logger.info("Push delivery unavailable for subscription %s", subscription.id)


class WebPushSender:
    def __init__(self, private_key: str, subject: str):
        from pywebpush import webpush  # type: ignore[import-not-found]  # Optional deployment extra.
        self._webpush = webpush
        self._private_key = private_key
        self._subject = subject

    def send(self, subscription: PushSubscription, payload: dict) -> None:
        self._webpush(
            subscription_info={"endpoint": subscription.endpoint, "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth}},
            data=json.dumps(payload), vapid_private_key=self._private_key,
            vapid_claims={"sub": self._subject},
        )


def default_sender() -> PushSender:
    from app.core.config import settings
    if settings.VAPID_PRIVATE_KEY and settings.VAPID_SUBJECT:
        try:
            return WebPushSender(settings.VAPID_PRIVATE_KEY, settings.VAPID_SUBJECT)
        except ImportError:
            logger.warning("pywebpush is unavailable; push delivery is log only")
    return LoggingPushSender()


class NotificationDispatcher:
    def __init__(self, sender: PushSender | None = None):
        self.sender = sender or default_sender()

    def dispatch(self, db: Session, *, user_ids: list[UUID], category: str, title: str,
                 message: str, related_entity_type: str | None = None,
                 related_entity_id: UUID | None = None) -> None:
        for user_id in user_ids:
            preference = db.get(NotificationPreference, (user_id, category))
            if preference is not None and not preference.enabled:
                continue
            notification = Notification(user_id=user_id, type=category, title=title,
                                        message=message, is_read=False,
                                        related_entity_type=related_entity_type,
                                        related_entity_id=related_entity_id)
            db.add(notification)
            db.commit()
            subscriptions = db.scalars(select(PushSubscription).where(PushSubscription.user_id == user_id)).all()
            for subscription in subscriptions:
                try:
                    self.sender.send(subscription, {"title": title, "body": message,
                                                    "notification_id": str(notification.id)})
                except Exception:
                    logger.exception("Push delivery failed for subscription %s", subscription.id)


def dispatch_in_background(user_ids: list[UUID], category: str, title: str, message: str,
                           related_entity_type: str | None = None,
                           related_entity_id: UUID | None = None) -> None:
    from app.core.database import SessionLocal
    try:
        with SessionLocal() as db:
            NotificationDispatcher().dispatch(db, user_ids=user_ids, category=category,
                title=title, message=message, related_entity_type=related_entity_type,
                related_entity_id=related_entity_id)
    except Exception:
        logger.exception("Notification dispatch failed")
