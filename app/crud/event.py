import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundError
from app.models.event import Event
from app.models.event_participant import EventParticipant
from app.models.user import User


def create_event(
    db: Session,
    *,
    group_id: uuid.UUID,
    title: str,
    description: str | None,
    cover_image_url: str | None,
    location: str,
    start_time: datetime,
    end_time: datetime,
) -> Event:
    event = Event(
        group_id=group_id,
        title=title.strip(),
        description=description.strip() if description else None,
        cover_image_url=cover_image_url.strip() if cover_image_url else None,
        location=location.strip(),
        start_time=start_time,
        end_time=end_time,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_events(
    db: Session,
    *,
    group_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Event]:
    stmt = select(Event)
    if group_id is not None:
        stmt = stmt.where(Event.group_id == group_id)

    stmt = stmt.order_by(Event.start_time.asc()).offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


def get_event(db: Session, event_id: uuid.UUID) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise ResourceNotFoundError("Event not found.")
    return event


def update_event(
    db: Session,
    *,
    db_obj: Event,
    update_data: dict[str, Any],
) -> Event:
    for field, value in update_data.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(db_obj, field, value)

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_event(db: Session, *, db_obj: Event) -> None:
    db.delete(db_obj)
    db.commit()


def list_upcoming_events_by_group(
    db: Session,
    *,
    group_id: uuid.UUID,
    from_time: datetime,
    limit: int = 3,
) -> list[Event]:
    stmt = (
        select(Event)
        .where(Event.group_id == group_id, Event.start_time >= from_time)
        .order_by(Event.start_time.asc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def get_event_by_title_for_group(
    db: Session,
    *,
    group_id: uuid.UUID,
    title: str,
) -> Event | None:
    stmt = select(Event).where(Event.group_id == group_id, Event.title == title.strip())
    return db.scalar(stmt)


def get_event_participant(
    db: Session,
    *,
    event_id: uuid.UUID,
    user_id: uuid.UUID,
) -> EventParticipant | None:
    stmt = select(EventParticipant).where(
        EventParticipant.event_id == event_id,
        EventParticipant.user_id == user_id,
    )
    return db.scalar(stmt)


def ensure_event_participant(
    db: Session,
    *,
    event_id: uuid.UUID,
    user_id: uuid.UUID,
) -> EventParticipant:
    participant = get_event_participant(db, event_id=event_id, user_id=user_id)
    if participant is not None:
        return participant

    participant = EventParticipant(event_id=event_id, user_id=user_id)
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant


def remove_event_participant(
    db: Session,
    *,
    event_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    participant = get_event_participant(db, event_id=event_id, user_id=user_id)
    if participant is None:
        return

    db.delete(participant)
    db.commit()


def list_event_participants(
    db: Session,
    *,
    event_id: uuid.UUID,
) -> list[User]:
    stmt = (
        select(User)
        .join(EventParticipant, EventParticipant.user_id == User.id)
        .where(EventParticipant.event_id == event_id)
        .order_by(EventParticipant.joined_at.asc())
    )
    return list(db.scalars(stmt).all())


def count_event_participants(
    db: Session,
    *,
    event_id: uuid.UUID,
) -> int:
    return len(list_event_participants(db, event_id=event_id))
