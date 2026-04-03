import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundError
from app.models.payment import Payment
from app.utils.enums import PaymentStatus


def create_payment(
    db: Session,
    *,
    user_id: uuid.UUID,
    amount: Decimal,
    currency: str,
    status: PaymentStatus,
    start_date: date,
    end_date: date,
) -> Payment:
    payment = Payment(
        user_id=user_id,
        amount=amount,
        currency=currency,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def list_payments_by_user(
    db: Session,
    *,
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[Payment]:
    stmt = (
        select(Payment)
        .where(Payment.user_id == user_id)
        .order_by(Payment.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def get_payment_for_user(
    db: Session,
    *,
    payment_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Payment:
    stmt = select(Payment).where(
        Payment.id == payment_id,
        Payment.user_id == user_id,
    )
    payment = db.scalar(stmt)
    if payment is None:
        raise ResourceNotFoundError("Payment not found.")
    return payment


def get_latest_completed_payment_for_user(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> Payment | None:
    stmt = (
        select(Payment)
        .where(
            Payment.user_id == user_id,
            Payment.status == PaymentStatus.COMPLETED,
        )
        .order_by(Payment.end_date.desc(), Payment.created_at.desc())
        .limit(1)
    )
    return db.scalar(stmt)


def create_completed_membership_payment(
    db: Session,
    *,
    user_id: uuid.UUID,
    amount: Decimal,
    currency: str,
    start_date: date,
    end_date: date,
) -> Payment:
    return create_payment(
        db,
        user_id=user_id,
        amount=amount,
        currency=currency,
        status=PaymentStatus.COMPLETED,
        start_date=start_date,
        end_date=end_date,
    )
