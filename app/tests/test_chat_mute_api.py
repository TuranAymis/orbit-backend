from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud import chat_room_state as chat_room_state_crud
from app.crud import group as group_crud
from app.crud import membership as membership_crud
from app.models.notification import Notification
from app.utils.enums import ChatRoomType, MembershipRole, MembershipStatus, UserRole


def _group(db: Session, owner_id):
    return group_crud.create_group(
        db,
        name="Muted Chat Group",
        description=None,
        cover_image_url=None,
        category=None,
        location=None,
        owner_id=owner_id,
    )


def _add_member(db: Session, *, group_id, user_id) -> None:
    membership_crud.create_membership(
        db,
        user_id=user_id,
        group_id=group_id,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )


def _event_payload(group_id) -> dict:
    starts_at = datetime.now(UTC) + timedelta(days=1)
    return {
        "group_id": str(group_id),
        "title": "Mute Test Event",
        "location": "Istanbul",
        "start_time": starts_at.isoformat(),
        "end_time": (starts_at + timedelta(hours=2)).isoformat(),
    }


def test_mute_and_unmute_persist_and_state_reflects_them(
    client, db_session: Session, make_user, auth_headers,
) -> None:
    owner = make_user("mute-owner@example.com")
    member = make_user("mute-member@example.com")
    group = _group(db_session, owner.id)
    _add_member(db_session, group_id=group.id, user_id=member.id)
    headers = auth_headers(member)
    room = {"room_type": "group", "room_id": str(group.id)}

    muted = client.put("/chat-rooms/mute", json=room, headers=headers)
    state = client.get("/chat-rooms/state", params=room, headers=headers)

    assert muted.status_code == state.status_code == 200
    assert muted.json()["is_muted"] is True
    assert state.json()["is_muted"] is True
    persisted = chat_room_state_crud.get_chat_room_state(
        db_session, user_id=member.id, room_type=ChatRoomType.GROUP, room_id=group.id,
    )
    assert persisted is not None and persisted.is_muted is True

    unmuted = client.delete("/chat-rooms/mute", params=room, headers=headers)
    state = client.get("/chat-rooms/state", params=room, headers=headers)

    assert unmuted.status_code == state.status_code == 200
    assert unmuted.json()["is_muted"] is False
    assert state.json()["is_muted"] is False
    db_session.refresh(persisted)
    assert persisted.is_muted is False
    assert persisted.muted_until is None


def test_expired_mute_does_not_suppress_chat_notification(
    client, db_session: Session, make_user, auth_headers,
) -> None:
    owner = make_user("expired-owner@example.com")
    member = make_user("expired-member@example.com")
    group = _group(db_session, owner.id)
    _add_member(db_session, group_id=group.id, user_id=member.id)
    room = {"room_type": "group", "room_id": str(group.id)}
    assert client.put("/chat-rooms/mute", json=room, headers=auth_headers(member)).status_code == 200
    state = chat_room_state_crud.get_chat_room_state(
        db_session, user_id=member.id, room_type=ChatRoomType.GROUP, room_id=group.id,
    )
    state.muted_until = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    assert chat_room_state_crud.list_muted_user_ids(
        db_session, room_type=ChatRoomType.GROUP, room_id=group.id, user_ids=[member.id],
    ) == set()
    created = client.post(
        "/chats", json={"group_id": str(group.id), "content": "Still delivered"},
        headers=auth_headers(owner),
    )
    assert created.status_code == 201
    notifications = db_session.scalars(select(Notification).where(
        Notification.user_id == member.id, Notification.type == "chat_message",
    )).all()
    assert len(notifications) == 1


def test_event_push_skips_muted_group_member_and_chat_remains_readable(
    client, db_session: Session, make_user, auth_headers, monkeypatch,
) -> None:
    owner = make_user("event-mute-owner@example.com", role=UserRole.ADMIN)
    muted_member = make_user("event-mute-member@example.com")
    other_member = make_user("event-other-member@example.com")
    group = _group(db_session, owner.id)
    _add_member(db_session, group_id=group.id, user_id=muted_member.id)
    _add_member(db_session, group_id=group.id, user_id=other_member.id)
    room = {"room_type": "group", "room_id": str(group.id)}
    assert client.put(
        "/chat-rooms/mute", json=room, headers=auth_headers(muted_member),
    ).status_code == 200

    dispatched = []
    monkeypatch.setattr(
        "app.services.push_dispatcher.dispatch_in_background",
        lambda user_ids, *args: dispatched.append((user_ids, args)),
    )
    created = client.post("/events", json=_event_payload(group.id), headers=auth_headers(owner))

    assert created.status_code == 201
    assert len(dispatched) == 1
    assert dispatched[0][0] == [other_member.id]
    assert dispatched[0][1][0] == "event"

    message = client.post(
        "/chats", json={"group_id": str(group.id), "content": "Visible while muted"},
        headers=auth_headers(owner),
    )
    history = client.get(
        "/chats", params={"group_id": str(group.id)}, headers=auth_headers(muted_member),
    )
    assert message.status_code == 201
    assert history.status_code == 200
    assert [item["content"] for item in history.json()] == ["Visible while muted"]
    state = client.get("/chat-rooms/state", params=room, headers=auth_headers(muted_member))
    assert state.status_code == 200
    assert state.json()["unread_count"] == 1
    notifications = db_session.scalars(select(Notification).where(
        Notification.type == "chat_message",
    )).all()
    assert {notification.user_id for notification in notifications} == {other_member.id}
