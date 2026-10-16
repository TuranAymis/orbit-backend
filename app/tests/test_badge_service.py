from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from app.models.user_badge import UserBadge
from app.crud import chat as chat_crud
from app.crud import event as event_crud
from app.crud import group as group_crud
from app.crud import membership as membership_crud
from app.services import badge_service
from app.utils.enums import MembershipRole, MembershipStatus


def test_registry_keys_are_unique() -> None:
    assert {rule.key for rule in badge_service.BADGE_RULES} == {
        "first_group_joined", "first_event_joined", "first_message_sent", "profile_completed"
    }
    assert all(rule.title and rule.description for rule in badge_service.BADGE_RULES)


def test_evaluate_badges_skips_existing_awards(monkeypatch) -> None:
    rule = badge_service.BadgeRule("test", "Test", "Test badge", lambda db, user_id: True)
    monkeypatch.setattr(badge_service, "BADGE_RULES", [rule])
    db = MagicMock()
    db.scalars.return_value.all.return_value = ["test"]

    assert badge_service.evaluate_badges(db, uuid4()) == []
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_evaluate_badges_handles_unique_constraint_race(monkeypatch) -> None:
    rule = badge_service.BadgeRule("test", "Test", "Test badge", lambda db, user_id: True)
    monkeypatch.setattr(badge_service, "BADGE_RULES", [rule])
    db = MagicMock()
    db.scalars.return_value.all.return_value = []
    db.begin_nested.return_value = nullcontext()
    db.flush.side_effect = IntegrityError("INSERT", {}, Exception("duplicate"))

    assert badge_service.evaluate_badges(db, uuid4()) == []
    assert isinstance(db.add.call_args.args[0], UserBadge)
    db.commit.assert_not_called()


def test_badge_endpoint_and_idempotency(db_session, client, auth_headers, make_user) -> None:
    """Runs only with ORBIT_TEST_DATABASE_URL via the shared integration fixture."""
    test_user = make_user("badges@example.com")
    headers = auth_headers(test_user)
    first = client.get("/users/me/badges", headers=headers)
    assert first.status_code == 200
    assert len(first.json()) == len(badge_service.BADGE_RULES)
    assert all(not badge["earned"] and badge["awarded_at"] is None for badge in first.json())

    test_user.bio = "Community builder"
    test_user.location = "Istanbul"
    test_user.avatar_url = "https://example.com/avatar.png"
    db_session.commit()
    assert badge_service.evaluate_badges(db_session, test_user.id) == ["profile_completed"]
    assert badge_service.evaluate_badges(db_session, test_user.id) == []
    earned = client.get("/users/me/badges", headers=headers).json()
    assert next(b for b in earned if b["key"] == "profile_completed")["awarded_at"]


def test_activity_rules_award_once(db_session, make_user) -> None:
    owner = make_user("badge-owner@example.com")
    member = make_user("badge-member@example.com")
    group = group_crud.create_group(
        db_session, name="Badge group", description=None, cover_image_url=None,
        category=None, location=None, owner_id=owner.id,
    )
    membership_crud.create_membership(
        db_session, user_id=member.id, group_id=group.id,
        role=MembershipRole.MEMBER, status=MembershipStatus.ACTIVE,
    )
    start = datetime.now(UTC) + timedelta(days=1)
    event = event_crud.create_event(
        db_session, group_id=group.id, title="Badge event", description=None,
        cover_image_url=None, location="Istanbul", start_time=start,
        end_time=start + timedelta(hours=2),
    )
    event_crud.ensure_event_participant(db_session, event_id=event.id, user_id=member.id)
    chat_crud.create_chat(
        db_session, sender_id=member.id, group_id=group.id,
        event_id=None, message="Hello!",
    )

    assert badge_service.evaluate_badges(db_session, member.id) == [
        "first_group_joined", "first_event_joined", "first_message_sent"
    ]
    assert badge_service.evaluate_badges(db_session, member.id) == []
