import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateResourceError
from app.models.membership import Membership
from app.utils.enums import MembershipRole, MembershipStatus


def get_membership_by_user_group(
    db: Session,
    *,
    user_id: uuid.UUID,
    group_id: uuid.UUID,
) -> Membership | None:
    stmt = select(Membership).where(
        Membership.user_id == user_id,
        Membership.group_id == group_id,
    )
    return db.scalar(stmt)


def create_membership(
    db: Session,
    *,
    user_id: uuid.UUID,
    group_id: uuid.UUID,
    role: MembershipRole,
    status: MembershipStatus,
) -> Membership:
    if get_membership_by_user_group(db, user_id=user_id, group_id=group_id):
        raise DuplicateResourceError("This user already has a membership for the group.")

    membership = Membership(
        user_id=user_id,
        group_id=group_id,
        role=role,
        status=status,
    )
    db.add(membership)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateResourceError("This user already has a membership for the group.") from exc

    db.refresh(membership)
    return membership


def list_memberships_by_group(
    db: Session,
    *,
    group_id: uuid.UUID,
) -> list[Membership]:
    stmt = (
        select(Membership)
        .where(Membership.group_id == group_id)
        .order_by(Membership.joined_at.asc())
    )
    return list(db.scalars(stmt).all())
