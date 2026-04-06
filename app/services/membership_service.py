from datetime import UTC, datetime, time

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.crud import payment as payment_crud
from app.crud import user as user_crud
from app.models.user import User
from app.schemas.membership import MembershipOverviewResponse, MembershipUpgradeResponse
from app.utils.enums import MembershipLevel


def _map_membership_tier(membership_level: MembershipLevel) -> str:
    return "premium" if membership_level == MembershipLevel.PAID else "free"


def _payment_date_to_datetime(value) -> datetime:
    return datetime.combine(value, time.min, tzinfo=UTC)


def get_membership_overview(db: Session, *, user: User) -> MembershipOverviewResponse:
    latest_payment = payment_crud.get_latest_completed_payment_for_user(db, user_id=user.id)
    is_paid = user.membership_level == MembershipLevel.PAID
    started_at = (
        _payment_date_to_datetime(latest_payment.start_date)
        if is_paid and latest_payment
        else None
    )
    renews_at = (
        _payment_date_to_datetime(latest_payment.end_date)
        if is_paid and latest_payment
        else None
    )

    return MembershipOverviewResponse(
        tier=_map_membership_tier(user.membership_level),
        status="active",
        started_at=started_at,
        renews_at=renews_at,
        benefits=[],
        limits={},
    )


def upgrade_membership(db: Session, *, user: User) -> MembershipUpgradeResponse:
    latest_payment = payment_crud.get_latest_completed_payment_for_user(db, user_id=user.id)
    if latest_payment is None:
        raise AppException("A completed payment is required before upgrading membership.")

    today = datetime.now(UTC).date()
    if latest_payment.start_date > today or latest_payment.end_date < today:
        raise AppException("Your completed payment is not active for the current billing period.")

    if user.membership_level != MembershipLevel.PAID:
        user = user_crud.update_membership_level(
            db,
            user=user,
            membership_level=MembershipLevel.PAID,
        )

    return MembershipUpgradeResponse(success=True, tier="premium")
