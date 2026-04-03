import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateResourceError, ResourceNotFoundError
from app.models.user import User
from app.utils.enums import MembershipLevel


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def get_user(db: Session, user_id: uuid.UUID) -> User:
    user = get_user_by_id(db, user_id)
    if user is None:
        raise ResourceNotFoundError("User not found.")
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    normalized_email = email.strip().lower()
    stmt = select(User).where(User.email == normalized_email)
    return db.scalar(stmt)


def create_user(
    db: Session,
    *,
    full_name: str,
    email: str,
    password_hash: str,
    membership_level: MembershipLevel,
) -> User:
    normalized_email = email.strip().lower()
    if get_user_by_email(db, normalized_email):
        raise DuplicateResourceError("A user with this email already exists.")

    user = User(
        full_name=full_name.strip(),
        email=normalized_email,
        password_hash=password_hash,
        membership_level=membership_level,
    )
    db.add(user)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateResourceError("A user with this email already exists.") from exc

    db.refresh(user)
    return user
