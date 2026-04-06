from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from app.core.exceptions import AppException
from app.services.membership_service import upgrade_membership
from app.utils.enums import MembershipLevel


def _user(level: MembershipLevel = MembershipLevel.FREE) -> SimpleNamespace:
    return SimpleNamespace(id="user_1", membership_level=level)


def _payment(start_delta_days: int = -1, end_delta_days: int = 30) -> SimpleNamespace:
    today = datetime.now(UTC).date()
    return SimpleNamespace(
        start_date=today + timedelta(days=start_delta_days),
        end_date=today + timedelta(days=end_delta_days),
    )


class UpgradeMembershipTests(TestCase):
    def test_rejects_without_completed_payment(self) -> None:
        db = object()
        user = _user()

        with patch(
            "app.services.membership_service.payment_crud.get_latest_completed_payment_for_user",
            return_value=None,
        ):
            with self.assertRaises(AppException) as exc:
                upgrade_membership(db, user=user)

        self.assertIn("completed payment is required", exc.exception.detail.lower())

    def test_rejects_when_payment_is_not_current(self) -> None:
        db = object()
        user = _user()

        with patch(
            "app.services.membership_service.payment_crud.get_latest_completed_payment_for_user",
            return_value=_payment(start_delta_days=-60, end_delta_days=-1),
        ):
            with self.assertRaises(AppException) as exc:
                upgrade_membership(db, user=user)

        self.assertIn("not active", exc.exception.detail.lower())

    def test_promotes_user_when_payment_is_valid(self) -> None:
        db = object()
        user = _user()
        upgraded_user = _user(level=MembershipLevel.PAID)

        with patch(
            "app.services.membership_service.payment_crud.get_latest_completed_payment_for_user",
            return_value=_payment(),
        ), patch(
            "app.services.membership_service.user_crud.update_membership_level",
            return_value=upgraded_user,
        ) as update_membership_level:
            result = upgrade_membership(db, user=user)

        update_membership_level.assert_called_once()
        self.assertTrue(result.success)
        self.assertEqual(result.tier, "premium")
