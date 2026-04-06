import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.group_moderator import GroupModerator


def get_group_moderator(
    db: Session,
    *,
    group_id: uuid.UUID,
    user_id: uuid.UUID,
) -> GroupModerator | None:
    stmt = select(GroupModerator).where(
        GroupModerator.group_id == group_id,
        GroupModerator.user_id == user_id,
    )
    return db.scalar(stmt)


def ensure_group_moderator(
    db: Session,
    *,
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    assigned_by: uuid.UUID,
) -> GroupModerator:
    existing_assignment = get_group_moderator(db, group_id=group_id, user_id=user_id)
    if existing_assignment is not None:
        return existing_assignment

    assignment = GroupModerator(
        group_id=group_id,
        user_id=user_id,
        assigned_by=assigned_by,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def remove_group_moderator(
    db: Session,
    *,
    group_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    assignment = get_group_moderator(db, group_id=group_id, user_id=user_id)
    if assignment is None:
        return

    db.delete(assignment)
    db.commit()
