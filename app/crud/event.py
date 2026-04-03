import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundError
from app.models.event import Event


def create_event(
    db: Session,
    *,
    group_id: uuid.UUID,
    title: str,
    description: str | None,
    location: str,
    start_time: datetime,
    end_time: datetime,
) -> Event:
    event = Event(
        group_id=group_id,
        title=title.strip(),
        description=description.strip() if description else None,
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
