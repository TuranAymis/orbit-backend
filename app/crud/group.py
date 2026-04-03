import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundError
from app.models.group import Group
from app.models.membership import Membership
from app.utils.enums import MembershipRole, MembershipStatus


def create_group(
    db: Session,
    *,
    name: str,
    description: str | None,
    owner_id: uuid.UUID,
) -> Group:
    group = Group(
        name=name.strip(),
        description=description.strip() if description else None,
        owner_id=owner_id,
    )
    db.add(group)
    db.flush()

    owner_membership = Membership(
        user_id=owner_id,
        group_id=group.id,
        role=MembershipRole.OWNER,
        status=MembershipStatus.ACTIVE,
    )
    db.add(owner_membership)
    db.commit()
    db.refresh(group)
    return group


def list_groups(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[Group]:
    stmt = select(Group).order_by(Group.created_at.desc()).offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


def get_group(db: Session, group_id: uuid.UUID) -> Group:
    group = db.get(Group, group_id)
    if group is None:
        raise ResourceNotFoundError("Group not found.")
    return group


def update_group(
    db: Session,
    *,
    db_obj: Group,
    update_data: dict[str, Any],
) -> Group:
    for field, value in update_data.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(db_obj, field, value)

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_group(db: Session, *, db_obj: Group) -> None:
    db.delete(db_obj)
    db.commit()
