from collections.abc import Generator
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_access_token
from app.models.user import User
from app.schemas.token import TokenPayload
from app.utils.enums import UserRole


bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DBSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DBSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Not authenticated.")

    try:
        payload = decode_access_token(credentials.credentials)
        token_data = TokenPayload.model_validate(payload)
        user_id = UUID(token_data.sub)
    except (JWTError, ValidationError, ValueError) as exc:
        raise AuthenticationError("Could not validate credentials.") from exc

    user = db.get(User, user_id)
    if user is None:
        raise AuthenticationError("Could not validate credentials.")
    if not user.is_active:
        raise AuthorizationError("Inactive user account.")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_optional_current_user(
    db: DBSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User | None:
    if credentials is None:
        return None
    if credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Not authenticated.")
    return get_current_user(db, credentials)


OptionalCurrentUser = Annotated[User | None, Depends(get_optional_current_user)]


def require_admin(current_user: CurrentUser) -> User:
    if current_user.role != UserRole.ADMIN:
        raise AuthorizationError("Admin access is required.")
    return current_user


CurrentAdmin = Annotated[User, Depends(require_admin)]


def require_moderator_or_admin(current_user: CurrentUser) -> User:
    if current_user.role not in {UserRole.MODERATOR, UserRole.ADMIN}:
        raise AuthorizationError("Moderator or admin access is required.")
    return current_user


CurrentModeratorOrAdmin = Annotated[User, Depends(require_moderator_or_admin)]
