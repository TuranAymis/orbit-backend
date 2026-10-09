import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateResourceError
from app.models.membership import Membership
from app.models.user import User
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


def list_active_group_ids_by_user(db: Session, *, user_id: uuid.UUID) -> set[uuid.UUID]:
    stmt = select(Membership.group_id).where(
        Membership.user_id == user_id,
        Membership.status == MembershipStatus.ACTIVE,
    )
    return set(db.scalars(stmt).all())


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


def count_memberships_by_group(
    db: Session,
    *,
    group_id: uuid.UUID,
) -> int:
    return sum(
        1
        for membership in list_memberships_by_group(db, group_id=group_id)
        if membership.status == MembershipStatus.ACTIVE
    )


def list_group_users(
    db: Session,
    *,
    group_id: uuid.UUID,
) -> list[User]:
    stmt = (
        select(User)
        .join(Membership, Membership.user_id == User.id)
        .where(
            Membership.group_id == group_id,
            Membership.status == MembershipStatus.ACTIVE,
        )
        .order_by(Membership.joined_at.asc())
    )
    return list(db.scalars(stmt).all())


def ensure_group_membership(
    db: Session,
    *,
    user_id: uuid.UUID,
    group_id: uuid.UUID,
    role: MembershipRole = MembershipRole.MEMBER,
    status: MembershipStatus = MembershipStatus.ACTIVE,
) -> Membership:
    membership = get_membership_by_user_group(db, user_id=user_id, group_id=group_id)
    if membership is not None:
        if membership.status != status:
            membership.status = status
            db.add(membership)
            db.commit()
            db.refresh(membership)
        return membership

    return create_membership(
        db,
        user_id=user_id,
        group_id=group_id,
        role=role,
        status=status,
    )


def remove_group_membership(
    db: Session,
    *,
    user_id: uuid.UUID,
    group_id: uuid.UUID,
) -> bool:
    membership = get_membership_by_user_group(db, user_id=user_id, group_id=group_id)
    if membership is None or membership.status == MembershipStatus.BANNED:
        # A ban must survive "leave"; otherwise the user could clear it and rejoin.
        return False

    db.delete(membership)
    db.commit()
    return True
