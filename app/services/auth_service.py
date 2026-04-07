from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
)
from app.core.security import (
    create_access_token,
    generate_verification_code,
    hash_password,
    hash_verification_code,
    verify_password,
    verify_verification_code,
)
from app.crud import auth_audit_log as auth_audit_log_crud
from app.crud import email_verification_code as verification_code_crud
from app.crud import user as user_crud
from app.models.user import User
from app.schemas.auth import (
    AuthActionResponse,
    LoginRequest,
    RegisterRequest,
    ResendVerificationCodeRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.services import email_service


def _record_auth_event(
    db: Session,
    *,
    event_type: str,
    email: str | None = None,
    user: User | None = None,
    detail: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> None:
    auth_audit_log_crud.create_auth_audit_log(
        db,
        event_type=event_type,
        email=email or (user.email if user else None),
        user_id=user.id if user else None,
        detail=detail,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata_json=metadata_json,
    )


def _enforce_rate_limit(
    db: Session,
    *,
    email: str,
    event_type: str,
    window_minutes: int,
    max_attempts: int,
    detail: str,
) -> None:
    recent_attempts = auth_audit_log_crud.count_recent_events_by_email(
        db,
        email=email,
        event_type=event_type,
        within=timedelta(minutes=window_minutes),
    )
    if recent_attempts >= max_attempts:
        raise RateLimitError(detail)


def _enforce_resend_cooldown(db: Session, *, email: str) -> None:
    latest_resend = auth_audit_log_crud.get_latest_event_by_email(
        db,
        email=email,
        event_type="verification_resend_requested",
    )
    if latest_resend is None:
        return

    cooldown_deadline = latest_resend.created_at + timedelta(
        seconds=settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS
    )
    if cooldown_deadline > datetime.now(UTC):
        raise RateLimitError("Please wait before requesting another verification code.")


def _issue_email_verification_code(
    db: Session,
    *,
    user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> str:
    code = generate_verification_code()
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.EMAIL_VERIFICATION_CODE_EXPIRE_MINUTES
    )
    verification_code = verification_code_crud.create_verification_code(
        db,
        user_id=user.id,
        email=user.email,
        code_hash=hash_verification_code(code),
        expires_at=expires_at,
    )
    _record_auth_event(
        db,
        event_type="verification_code_generated",
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata_json={
            "verification_code_id": str(verification_code.id),
            "expires_at": verification_code.expires_at.isoformat(),
        },
    )
    email_service.send_verification_code_email(email=user.email, code=code)
    _record_auth_event(
        db,
        event_type="verification_email_sent",
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata_json={"verification_code_id": str(verification_code.id)},
    )
    return code


def register_user(
    db: Session,
    *,
    payload: RegisterRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuthActionResponse:
    _enforce_rate_limit(
        db,
        email=str(payload.email),
        event_type="register_started",
        window_minutes=settings.AUTH_REGISTER_RATE_LIMIT_WINDOW_MINUTES,
        max_attempts=settings.AUTH_REGISTER_RATE_LIMIT_MAX_ATTEMPTS,
        detail="Too many registration attempts. Please try again later.",
    )
    _record_auth_event(
        db,
        event_type="register_started",
        email=str(payload.email),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    password_hash = hash_password(payload.password)
    resolved_full_name = payload.full_name
    if resolved_full_name is None:
        email_prefix = str(payload.email).split("@", 1)[0].replace(".", " ").replace("_", " ")
        resolved_full_name = email_prefix.title() or "Orbit User"
    user = user_crud.create_user(
        db,
        full_name=resolved_full_name,
        email=payload.email,
        password_hash=password_hash,
        membership_level=payload.membership_level,
        is_active=False,
    )
    _record_auth_event(
        db,
        event_type="register_completed",
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    _issue_email_verification_code(
        db,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return AuthActionResponse(message="Verification code sent to email")


def authenticate_user(
    db: Session,
    *,
    email: str,
    password: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> User:
    user = user_crud.get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        raise AuthenticationError("Incorrect email or password.")
    if not user.is_active:
        _record_auth_event(
            db,
            event_type="login_blocked_unverified",
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise AuthorizationError("Email not verified")
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


def login_user(
    db: Session,
    *,
    payload: LoginRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> TokenResponse:
    user = authenticate_user(
        db,
        email=payload.email,
        password=payload.password,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return issue_access_token(user)


def verify_email_code(
    db: Session,
    *,
    payload: VerifyEmailRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuthActionResponse:
    _enforce_rate_limit(
        db,
        email=str(payload.email),
        event_type="verification_failed",
        window_minutes=settings.AUTH_VERIFY_RATE_LIMIT_WINDOW_MINUTES,
        max_attempts=settings.AUTH_VERIFY_RATE_LIMIT_MAX_ATTEMPTS,
        detail="Too many verification attempts. Please request a new code.",
    )
    user = user_crud.get_user_by_email(db, payload.email)
    if user is None:
        _record_auth_event(
            db,
            event_type="verification_failed",
            email=str(payload.email),
            detail="user_not_found",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise AppException("Invalid verification code.")

    if user.is_active:
        return AuthActionResponse(message="Account verified successfully")

    verification_code = verification_code_crud.get_latest_unused_code_by_email(
        db,
        email=payload.email,
    )
    if verification_code is None or verification_code.user_id != user.id:
        _record_auth_event(
            db,
            event_type="verification_failed",
            user=user,
            detail="code_not_found",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise AppException("Invalid verification code.")

    if verification_code_crud.is_code_expired(verification_code):
        verification_code_crud.mark_code_used(db, verification_code=verification_code)
        _record_auth_event(
            db,
            event_type="verification_failed",
            user=user,
            detail="code_expired",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise AppException("Verification code expired.")

    if not verify_verification_code(payload.code, verification_code.code_hash):
        verification_code = verification_code_crud.increment_attempt_count(
            db,
            verification_code=verification_code,
        )
        if verification_code.attempt_count >= settings.EMAIL_VERIFICATION_MAX_ATTEMPTS:
            verification_code_crud.mark_code_used(db, verification_code=verification_code)
        _record_auth_event(
            db,
            event_type="verification_failed",
            user=user,
            detail="invalid_code",
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_json={"attempt_count": verification_code.attempt_count},
        )
        raise AppException("Invalid verification code.")

    verification_code_crud.mark_code_used(db, verification_code=verification_code)
    user_crud.activate_user(db, user=user)
    _record_auth_event(
        db,
        event_type="verification_succeeded",
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return AuthActionResponse(message="Account verified successfully")


def resend_verification_code(
    db: Session,
    *,
    payload: ResendVerificationCodeRequest,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuthActionResponse:
    _enforce_rate_limit(
        db,
        email=str(payload.email),
        event_type="verification_resend_requested",
        window_minutes=settings.AUTH_RESEND_RATE_LIMIT_WINDOW_MINUTES,
        max_attempts=settings.AUTH_RESEND_RATE_LIMIT_MAX_ATTEMPTS,
        detail="Too many verification code requests. Please try again later.",
    )
    _enforce_resend_cooldown(db, email=str(payload.email))
    _record_auth_event(
        db,
        event_type="verification_resend_requested",
        email=str(payload.email),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    user = user_crud.get_user_by_email(db, payload.email)
    if user is None:
        return AuthActionResponse(message="Verification code sent")

    if user.is_active:
        return AuthActionResponse(message="Account already verified")

    _issue_email_verification_code(
        db,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return AuthActionResponse(message="Verification code sent")
