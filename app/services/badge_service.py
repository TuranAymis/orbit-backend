"""Small registry of badges earned from persisted user activity."""

import logging
from dataclasses import dataclass
from typing import Callable
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.chat import Chat
from app.models.event_participant import EventParticipant
from app.models.membership import Membership
from app.models.user import User
from app.models.user_badge import UserBadge
from app.utils.enums import MembershipStatus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BadgeRule:
    key: str
    title: str
    description: str
    check: Callable[[Session, UUID], bool]


def _has_active_group(db: Session, user_id: UUID) -> bool:
    return bool(db.scalar(select(exists().where(
        Membership.user_id == user_id, Membership.status == MembershipStatus.ACTIVE
    ))))


def _has_event(db: Session, user_id: UUID) -> bool:
    return bool(db.scalar(select(exists().where(EventParticipant.user_id == user_id))))


def _has_message(db: Session, user_id: UUID) -> bool:
    return bool(db.scalar(select(exists().where(Chat.sender_id == user_id))))


def _has_complete_profile(db: Session, user_id: UUID) -> bool:
    return bool(db.scalar(select(exists().where(
        User.id == user_id,
        User.bio.is_not(None), User.bio != "",
        User.location.is_not(None), User.location != "",
        User.avatar_url.is_not(None), User.avatar_url != "",
    ))))


BADGE_RULES: list[BadgeRule] = [
    BadgeRule("first_group_joined", "First group", "Join your first group.", _has_active_group),
    BadgeRule("first_event_joined", "First event", "Join your first event.", _has_event),
    BadgeRule("first_message_sent", "First message", "Send your first chat message.", _has_message),
    BadgeRule("profile_completed", "Profile complete", "Add a bio, location, and avatar.", _has_complete_profile),
]


def evaluate_badges(db: Session, user_id: UUID) -> list[str]:
    """Persist newly earned badges. A savepoint absorbs concurrent unique-key races."""
    existing = set(db.scalars(select(UserBadge.badge_key).where(UserBadge.user_id == user_id)).all())
    awarded: list[str] = []
    for rule in BADGE_RULES:
        if rule.key in existing or not rule.check(db, user_id):
            continue
        try:
            with db.begin_nested():
                db.add(UserBadge(user_id=user_id, badge_key=rule.key))
                db.flush()
        except IntegrityError:
            # Another request awarded it between the existence check and insert.
            continue
        db.commit()
        awarded.append(rule.key)
    return awarded


def evaluate_badges_best_effort(db: Session, user_id: UUID) -> None:
    try:
        evaluate_badges(db, user_id)
    except Exception:
        logger.exception("Badge evaluation failed for user %s", user_id)
        db.rollback()
