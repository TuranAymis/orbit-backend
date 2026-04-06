import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event_moderator import EventModerator


def get_event_moderator(
    db: Session,
    *,
    event_id: uuid.UUID,
    user_id: uuid.UUID,
) -> EventModerator | None:
    stmt = select(EventModerator).where(
        EventModerator.event_id == event_id,
        EventModerator.user_id == user_id,
    )
    return db.scalar(stmt)


def ensure_event_moderator(
    db: Session,
    *,
    event_id: uuid.UUID,
    user_id: uuid.UUID,
    assigned_by: uuid.UUID,
) -> EventModerator:
    existing_assignment = get_event_moderator(db, event_id=event_id, user_id=user_id)
    if existing_assignment is not None:
        return existing_assignment

    assignment = EventModerator(
        event_id=event_id,
        user_id=user_id,
        assigned_by=assigned_by,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def remove_event_moderator(
    db: Session,
    *,
    event_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    assignment = get_event_moderator(db, event_id=event_id, user_id=user_id)
    if assignment is None:
        return

    db.delete(assignment)
    db.commit()
