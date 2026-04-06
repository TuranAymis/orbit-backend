import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateResourceError, ResourceNotFoundError
from app.models.user import User
from app.utils.enums import MembershipLevel, UserRole


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
    role: UserRole = UserRole.USER,
) -> User:
    normalized_email = email.strip().lower()
    if get_user_by_email(db, normalized_email):
        raise DuplicateResourceError("A user with this email already exists.")

    user = User(
        full_name=full_name.strip(),
        email=normalized_email,
        password_hash=password_hash,
        membership_level=membership_level,
        role=role,
    )
    db.add(user)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateResourceError("A user with this email already exists.") from exc

    db.refresh(user)
    return user


def update_user_profile(
    db: Session,
    *,
    user: User,
    full_name: str | None = None,
    bio: str | None = None,
    location: str | None = None,
    avatar_url: str | None = None,
) -> User:
    if full_name is not None:
        user.full_name = full_name.strip()
    if bio is not None:
        user.bio = bio.strip()
    if location is not None:
        user.location = location.strip()
    if avatar_url is not None:
        user.avatar_url = avatar_url.strip()

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_membership_level(
    db: Session,
    *,
    user: User,
    membership_level: MembershipLevel,
) -> User:
    user.membership_level = membership_level
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
