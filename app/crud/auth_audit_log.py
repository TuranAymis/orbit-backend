from datetime import UTC, datetime, timedelta
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.auth_audit_log import AuthAuditLog


def create_auth_audit_log(
    db: Session,
    *,
    event_type: str,
    email: str | None = None,
    user_id: uuid.UUID | None = None,
    detail: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> AuthAuditLog:
    audit_log = AuthAuditLog(
        event_type=event_type,
        email=email.strip().lower() if email else None,
        user_id=user_id,
        detail=detail,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata_json=metadata_json,
    )
    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)
    return audit_log


def count_recent_events_by_email(
    db: Session,
    *,
    email: str,
    event_type: str,
    within: timedelta,
) -> int:
    cutoff = datetime.now(UTC) - within
    stmt = select(func.count()).select_from(AuthAuditLog).where(
        AuthAuditLog.email == email.strip().lower(),
        AuthAuditLog.event_type == event_type,
        AuthAuditLog.created_at >= cutoff,
    )
    return int(db.scalar(stmt) or 0)


def get_latest_event_by_email(
    db: Session,
    *,
    email: str,
    event_type: str,
) -> AuthAuditLog | None:
    stmt = (
        select(AuthAuditLog)
        .where(
            AuthAuditLog.email == email.strip().lower(),
            AuthAuditLog.event_type == event_type,
        )
        .order_by(AuthAuditLog.created_at.desc())
    )
    return db.scalars(stmt).first()
