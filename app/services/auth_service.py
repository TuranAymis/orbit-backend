from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import create_access_token, hash_password, verify_password
from app.crud import user as user_crud
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse


def register_user(db: Session, *, payload: RegisterRequest) -> User:
    password_hash = hash_password(payload.password)
    return user_crud.create_user(
        db,
        full_name=payload.full_name,
        email=payload.email,
        password_hash=password_hash,
        membership_level=payload.membership_level,
    )


def authenticate_user(db: Session, *, email: str, password: str) -> User:
    user = user_crud.get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        raise AuthenticationError("Incorrect email or password.")
    if not user.is_active:
        raise AuthorizationError("Inactive user account.")
    return user


def issue_access_token(user: User) -> TokenResponse:
    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
    )


def login_user(db: Session, *, payload: LoginRequest) -> TokenResponse:
    user = authenticate_user(db, email=payload.email, password=payload.password)
    return issue_access_token(user)
