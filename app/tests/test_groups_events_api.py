from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.crud import chat as chat_crud
from app.crud import event as event_crud
from app.crud import group as group_crud
from app.crud import membership as membership_crud
from app.utils.enums import MembershipRole, MembershipStatus


def _group(db: Session, owner_id, name: str):
    return group_crud.create_group(
        db,
        name=name,
        description=f"Description for {name}",
        cover_image_url=None,
        category=None,
        location=None,
        owner_id=owner_id,
    )


def _event(db: Session, group_id):
    start = datetime.now(UTC) + timedelta(days=1)
    return event_crud.create_event(
        db,
        group_id=group_id,
        title="API Test Event",
        description="Event description",
        cover_image_url=None,
        location="Istanbul",
        start_time=start,
        end_time=start + timedelta(hours=2),
    )


def test_group_list_and_detail_show_membership_counts_and_joined_state(
    client, db_session: Session, make_user, auth_headers
) -> None:
    owner = make_user("group-owner@example.com")
    member = make_user("group-member@example.com")
    joined_group = _group(db_session, owner.id, "Joined Group")
    other_group = _group(db_session, owner.id, "Other Group")
    membership_crud.create_membership(
        db_session,
        user_id=member.id,
        group_id=joined_group.id,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )
    headers = auth_headers(member)

    response = client.get("/groups", headers=headers)

    assert response.status_code == 200
    groups = {item["id"]: item for item in response.json()}
    assert set(groups) == {str(joined_group.id), str(other_group.id)}
    assert groups[str(joined_group.id)]["member_count"] == 2  # owner and member
    assert groups[str(joined_group.id)]["is_joined"] is True
    assert groups[str(other_group.id)]["member_count"] == 1  # owner only
    assert groups[str(other_group.id)]["is_joined"] is False

    joined_detail = client.get(f"/groups/{joined_group.id}", headers=headers)
    other_detail = client.get(f"/groups/{other_group.id}", headers=headers)

    assert joined_detail.status_code == 200
    assert joined_detail.json()["member_count"] == 2
    assert joined_detail.json()["is_joined"] is True
    assert joined_detail.json()["stats"]["members"] == 2
    assert other_detail.status_code == 200
    assert other_detail.json()["member_count"] == 1
    assert other_detail.json()["is_joined"] is False


def test_group_join_and_leave_are_idempotent(
    client, db_session: Session, make_user, auth_headers
) -> None:
    owner = make_user("group-owner@example.com")
    member = make_user("group-member@example.com")
    group = _group(db_session, owner.id, "Membership Group")
    headers = auth_headers(member)

    first_join = client.post(f"/groups/{group.id}/members", headers=headers)
    repeated_join = client.post(f"/groups/{group.id}/members", headers=headers)

    assert first_join.status_code == repeated_join.status_code == 200
    assert first_join.json() == {
        "success": True, "group_id": str(group.id), "is_joined": True,
        "member_count": 2, "action": "joined",
    }
    assert repeated_join.json()["action"] == "already_joined"
    assert repeated_join.json()["member_count"] == 2

    first_leave = client.delete(f"/groups/{group.id}/members/me", headers=headers)
    repeated_leave = client.delete(f"/groups/{group.id}/members/me", headers=headers)

    assert first_leave.status_code == repeated_leave.status_code == 200
    assert first_leave.json() == {
        "success": True, "group_id": str(group.id), "is_joined": False,
        "member_count": 1, "action": "left",
    }
    assert repeated_leave.json()["action"] == "already_left"
    assert repeated_leave.json()["member_count"] == 1
    assert membership_crud.get_membership_by_user_group(
        db_session, user_id=member.id, group_id=group.id
    ) is None
    detail = client.get(f"/groups/{group.id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["is_joined"] is False
    assert detail.json()["member_count"] == 1


def test_group_detail_missing_and_invalid_id(client, make_user, auth_headers) -> None:
    headers = auth_headers(make_user("group-reader@example.com"))

    missing = client.get(f"/groups/{uuid4()}", headers=headers)
    invalid = client.get("/groups/not-a-uuid", headers=headers)

    assert missing.status_code == 404
    assert missing.json()["detail"] == "Group not found."
    assert invalid.status_code == 422


def test_event_list_detail_join_and_leave(
    client, db_session: Session, make_user, auth_headers
) -> None:
    owner = make_user("event-owner@example.com")
    attendee = make_user("event-attendee@example.com")
    group = _group(db_session, owner.id, "Event Group")
    event = _event(db_session, group.id)
    headers = auth_headers(attendee)

    listed = client.get("/events", params={"group_id": str(group.id)}, headers=headers)
    detail = client.get(f"/events/{event.id}", headers=headers)

    assert listed.status_code == detail.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == str(event.id)
    assert listed.json()[0]["title"] == "API Test Event"
    assert listed.json()[0]["attendee_count"] == 0
    assert listed.json()[0]["is_joined"] is False
    assert detail.json()["id"] == str(event.id)
    assert detail.json()["attendee_count"] == 0
    assert detail.json()["is_joined"] is False
    assert detail.json()["related_group"] == {"id": str(group.id), "name": group.name}

    first_join = client.post(f"/events/{event.id}/join", headers=headers)
    repeated_join = client.post(f"/events/{event.id}/join", headers=headers)

    assert first_join.status_code == repeated_join.status_code == 200
    assert first_join.json() == {
        "success": True, "event_id": str(event.id), "is_joined": True,
        "attendee_count": 1, "action": "joined",
    }
    assert repeated_join.json()["action"] == "already_joined"
    assert repeated_join.json()["attendee_count"] == 1
    joined_list = client.get("/events", params={"group_id": str(group.id)}, headers=headers)
    joined_detail = client.get(f"/events/{event.id}", headers=headers)
    assert joined_list.json()[0]["attendee_count"] == 1
    assert joined_list.json()[0]["is_joined"] is True
    assert joined_detail.json()["attendee_count"] == 1
    assert joined_detail.json()["is_joined"] is True
    assert joined_detail.json()["participants_preview"][0]["id"] == str(attendee.id)

    first_leave = client.post(f"/events/{event.id}/leave", headers=headers)
    repeated_leave = client.post(f"/events/{event.id}/leave", headers=headers)

    assert first_leave.status_code == repeated_leave.status_code == 200
    assert first_leave.json() == {
        "success": True, "event_id": str(event.id), "is_joined": False,
        "attendee_count": 0, "action": "left",
    }
    assert repeated_leave.json()["action"] == "already_left"
    assert repeated_leave.json()["attendee_count"] == 0
    after_leave = client.get(f"/events/{event.id}", headers=headers)
    assert after_leave.json()["attendee_count"] == 0
    assert after_leave.json()["is_joined"] is False


def test_event_join_missing_and_unauthenticated(client, make_user, auth_headers) -> None:
    event_id = uuid4()
    authenticated = client.post(
        f"/events/{event_id}/join",
        headers=auth_headers(make_user("event-reader@example.com")),
    )
    anonymous = client.post(f"/events/{event_id}/join")

    assert authenticated.status_code == 404
    assert authenticated.json()["detail"] == "Event not found."
    assert anonymous.status_code == 401


@pytest.mark.parametrize(
    ("membership_status", "expected_status"),
    [
        (MembershipStatus.PENDING, 403),
        (MembershipStatus.BANNED, 403),
        (MembershipStatus.ACTIVE, 200),
    ],
)
def test_group_chat_history_requires_active_membership(
    client, db_session: Session, make_user, auth_headers,
    membership_status: MembershipStatus, expected_status: int,
) -> None:
    owner = make_user("chat-owner@example.com")
    reader = make_user("chat-reader@example.com")
    group = _group(db_session, owner.id, "Chat Group")
    chat = chat_crud.create_chat(
        db_session,
        sender_id=owner.id,
        group_id=group.id,
        event_id=None,
        message="Existing group message",
    )
    membership_crud.create_membership(
        db_session,
        user_id=reader.id,
        group_id=group.id,
        role=MembershipRole.MEMBER,
        status=membership_status,
    )

    response = client.get(
        "/chats", params={"group_id": str(group.id)}, headers=auth_headers(reader)
    )

    assert response.status_code == expected_status
    if expected_status == 403:
        assert response.json()["detail"] == "Only active group members can access this chat."
    else:
        assert len(response.json()) == 1
        assert response.json()[0]["id"] == str(chat.id)
        assert response.json()[0]["content"] == "Existing group message"


def test_banned_member_cannot_rejoin_or_clear_ban_and_is_not_counted(
    client, db_session: Session, make_user, auth_headers,
) -> None:
    owner = make_user("ban-owner@example.com")
    banned = make_user("banned@example.com")
    group = _group(db_session, owner.id, "Ban Group")
    membership_crud.create_membership(
        db_session,
        user_id=banned.id,
        group_id=group.id,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.BANNED,
    )
    headers = auth_headers(banned)

    join = client.post(f"/groups/{group.id}/members", headers=headers)
    leave = client.delete(f"/groups/{group.id}/members/me", headers=headers)
    rejoin = client.post(f"/groups/{group.id}/members", headers=headers)
    detail = client.get(f"/groups/{group.id}", headers=headers)

    assert join.status_code == 403
    assert leave.status_code == 200 and leave.json()["action"] == "already_left"
    assert rejoin.status_code == 403
    assert detail.json()["member_count"] == 1  # owner only; banned/pending are not counted
