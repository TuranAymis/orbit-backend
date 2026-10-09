from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.routes.groups import get_group, list_groups
from app.models.group import Group  # noqa: F401 - resolves the membership foreign key
from app.models.membership import Membership
from app.models.user import User  # noqa: F401 - resolves the membership foreign key
from app.utils.enums import MembershipRole, MembershipStatus, UserRole


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Membership.__table__.create(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_group_list_marks_only_current_users_active_groups(db):
    user_id, other_user_id = uuid4(), uuid4()
    active_id, pending_id, banned_id, others_id, empty_id = [uuid4() for _ in range(5)]
    for member_id, group_id, status in [
        (user_id, active_id, MembershipStatus.ACTIVE),
        (user_id, pending_id, MembershipStatus.PENDING),
        (user_id, banned_id, MembershipStatus.BANNED),
        (other_user_id, others_id, MembershipStatus.ACTIVE),
    ]:
        db.add(Membership(user_id=member_id, group_id=group_id,
                          role=MembershipRole.MEMBER, status=status))
    db.commit()

    groups = [SimpleNamespace(id=group_id, name=f"Group {index}",
                              description=None, cover_image_url=None)
              for index, group_id in enumerate(
                  (active_id, pending_id, banned_id, others_id, empty_id))]
    with patch("app.api.routes.groups.group_crud.list_groups", return_value=groups), \
         patch("app.api.routes.groups.membership_crud.count_memberships_by_group", return_value=0):
        joined = list_groups(db, SimpleNamespace(id=user_id), skip=0, limit=100)
        anonymous = list_groups(db, None, skip=0, limit=100)
        other_user = list_groups(db, SimpleNamespace(id=other_user_id), skip=0, limit=100)

    assert [item.is_joined for item in joined] == [True, False, False, False, False]
    assert [item.is_joined for item in anonymous] == [False] * 5
    assert [item.is_joined for item in other_user] == [False, False, False, True, False]
    assert joined[0].model_dump(mode="json") == {
        "id": str(active_id), "name": "Group 0", "description": None,
        "member_count": 0, "image_url": None, "is_joined": True,
    }


def test_group_detail_does_not_mark_pending_membership_as_joined():
    group_id = uuid4()
    group = SimpleNamespace(
        id=group_id, name="Group", description=None, cover_image_url=None,
        category=None, location=None, owner=SimpleNamespace(id=uuid4(), full_name="Owner"),
        events=[],
    )
    with patch("app.api.routes.groups.group_crud.get_group", return_value=group), \
         patch("app.api.routes.groups.membership_crud.list_group_users", return_value=[]), \
         patch("app.api.routes.groups.membership_crud.get_membership_by_user_group",
               return_value=SimpleNamespace(status=MembershipStatus.PENDING)), \
         patch("app.api.routes.groups.event_crud.list_upcoming_events_by_group", return_value=[]):
        result = get_group(group_id, object(), SimpleNamespace(id=uuid4(), role=UserRole.USER))

    assert result.is_joined is False
