from datetime import UTC, datetime
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.email_verification_code import EmailVerificationCode


def invalidate_unused_codes_for_user(db: Session, *, user_id: uuid.UUID) -> None:
    stmt = select(EmailVerificationCode).where(
        EmailVerificationCode.user_id == user_id,
        EmailVerificationCode.is_used.is_(False),
    )
    codes = db.scalars(stmt).all()
    for code in codes:
        code.is_used = True
        db.add(code)


def create_verification_code(
    db: Session,
    *,
    user_id: uuid.UUID,
    email: str,
    code_hash: str,
    expires_at: datetime,
) -> EmailVerificationCode:
    invalidate_unused_codes_for_user(db, user_id=user_id)
    verification_code = EmailVerificationCode(
        user_id=user_id,
        email=email.strip().lower(),
        code_hash=code_hash,
        expires_at=expires_at,
        attempt_count=0,
        is_used=False,
    )
    db.add(verification_code)
    db.commit()
    db.refresh(verification_code)
    return verification_code


def get_latest_unused_code_by_email(
    db: Session,
    *,
    email: str,
) -> EmailVerificationCode | None:
    stmt = (
        select(EmailVerificationCode)
        .where(
            EmailVerificationCode.email == email.strip().lower(),
            EmailVerificationCode.is_used.is_(False),
        )
        .order_by(EmailVerificationCode.created_at.desc())
    )
    return db.scalars(stmt).first()


def mark_code_used(db: Session, *, verification_code: EmailVerificationCode) -> EmailVerificationCode:
    verification_code.is_used = True
    db.add(verification_code)
    db.commit()
    db.refresh(verification_code)
    return verification_code


def increment_attempt_count(
    db: Session,
    *,
    verification_code: EmailVerificationCode,
) -> EmailVerificationCode:
    verification_code.attempt_count += 1
    db.add(verification_code)
    db.commit()
    db.refresh(verification_code)
    return verification_code


def is_code_expired(verification_code: EmailVerificationCode) -> bool:
    return verification_code.expires_at <= datetime.now(UTC)
