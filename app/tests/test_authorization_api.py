from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.crud import event as event_crud
from app.crud import group as group_crud
from app.crud import group_moderator as group_moderator_crud
from app.utils.enums import UserRole


def _group(db: Session, owner_id, name: str):
    return group_crud.create_group(
        db,
        name=name,
        description=None,
        cover_image_url=None,
        category=None,
        location=None,
        owner_id=owner_id,
    )


def _event_payload(group_id) -> dict:
    start = datetime.now(UTC) + timedelta(days=1)
    return {
        "group_id": str(group_id),
        "title": "API Test Event",
        "location": "Istanbul",
        "start_time": start.isoformat(),
        "end_time": (start + timedelta(hours=2)).isoformat(),
    }


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [
        (UserRole.ADMIN, 201),
        (UserRole.MODERATOR, 403),
        (UserRole.USER, 403),
        (None, 401),
    ],
)
def test_group_create_requires_admin(client, make_user, auth_headers, role, expected_status):
    headers = (
        auth_headers(make_user(f"{role.value}@example.com", role=role)) if role else {}
    )

    response = client.post("/groups", json={"name": "Test Group"}, headers=headers)

    assert response.status_code == expected_status
    if role == UserRole.ADMIN:
        assert response.json()["name"] == "Test Group"


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [
        (UserRole.ADMIN, 204),
        (UserRole.MODERATOR, 403),
        (UserRole.USER, 403),
        (None, 401),
    ],
)
def test_group_delete_requires_admin(
    client, db_session, make_user, auth_headers, role, expected_status
):
    admin = make_user("admin@example.com", role=UserRole.ADMIN)
    group = _group(db_session, admin.id, "Delete Group")
    group_id = group.id
    actor = (
        admin if role == UserRole.ADMIN else
        make_user(f"{role.value}@example.com", role=role) if role else None
    )

    response = client.delete(
        f"/groups/{group_id}",
        headers=auth_headers(actor) if actor else {},
    )

    assert response.status_code == expected_status
    db_session.expunge_all()
    assert (db_session.get(type(group), group_id) is None) == (role == UserRole.ADMIN)


@pytest.mark.parametrize(
    ("role", "assigned", "expected_status"),
    [
        (UserRole.ADMIN, False, 201),
        (UserRole.MODERATOR, True, 201),
        (UserRole.MODERATOR, False, 403),
        (UserRole.USER, False, 403),
        (None, False, 401),
    ],
)
def test_event_create_obeys_group_scope(
    client, db_session, make_user, auth_headers, role, assigned, expected_status
):
    admin = make_user("admin@example.com", role=UserRole.ADMIN)
    moderated_group = _group(db_session, admin.id, "Moderated Group")
    other_group = _group(db_session, admin.id, "Other Group")
    actor = (
        admin if role == UserRole.ADMIN else
        make_user(f"{role.value}@example.com", role=role) if role else None
    )
    if role == UserRole.MODERATOR:
        group_moderator_crud.ensure_group_moderator(
            db_session,
            group_id=moderated_group.id,
            user_id=actor.id,
            assigned_by=admin.id,
        )
    target = moderated_group if assigned else other_group

    response = client.post(
        "/events", json=_event_payload(target.id),
        headers=auth_headers(actor) if actor else {},
    )

    assert response.status_code == expected_status
    if expected_status == 201:
        assert response.json()["group_id"] == str(target.id)


@pytest.mark.parametrize(
    ("role", "assigned", "expected_status"),
    [
        (UserRole.ADMIN, False, 204),
        (UserRole.MODERATOR, True, 204),
        (UserRole.MODERATOR, False, 403),
        (UserRole.USER, False, 403),
        (None, False, 401),
    ],
)
def test_event_delete_obeys_group_scope(
    client, db_session, make_user, auth_headers, role, assigned, expected_status
):
    admin = make_user("admin@example.com", role=UserRole.ADMIN)
    moderated_group = _group(db_session, admin.id, "Moderated Group")
    other_group = _group(db_session, admin.id, "Other Group")
    actor = (
        admin if role == UserRole.ADMIN else
        make_user(f"{role.value}@example.com", role=role) if role else None
    )
    if role == UserRole.MODERATOR:
        group_moderator_crud.ensure_group_moderator(
            db_session,
            group_id=moderated_group.id,
            user_id=actor.id,
            assigned_by=admin.id,
        )
    target = moderated_group if assigned else other_group
    start = datetime.now(UTC) + timedelta(days=1)
    event = event_crud.create_event(
        db_session,
        group_id=target.id,
        title="Delete Event",
        description=None,
        cover_image_url=None,
        location="Istanbul",
        start_time=start,
        end_time=start + timedelta(hours=2),
    )
    event_id = event.id

    response = client.delete(
        f"/events/{event_id}", headers=auth_headers(actor) if actor else {}
    )

    assert response.status_code == expected_status
    db_session.expunge_all()
    assert (db_session.get(type(event), event_id) is None) == (expected_status == 204)


def test_moderator_update_and_manage_flags_are_scoped_to_assigned_group(
    client, db_session, make_user, auth_headers,
) -> None:
    from datetime import UTC, datetime, timedelta

    from app.crud import event as event_crud
    from app.crud import group as group_crud
    from app.crud import group_moderator as group_moderator_crud
    from app.utils.enums import UserRole

    owner = make_user("scope-owner@example.com")
    moderator = make_user("scope-mod@example.com", role=UserRole.MODERATOR)
    admin = make_user("scope-admin@example.com", role=UserRole.ADMIN)
    own_group, other_group = [
        group_crud.create_group(
            db_session, name=name, description=None, cover_image_url=None,
            category=None, location=None, owner_id=owner.id,
        )
        for name in ("Moderated", "Unmoderated")
    ]
    group_moderator_crud.ensure_group_moderator(
        db_session, group_id=own_group.id, user_id=moderator.id, assigned_by=admin.id
    )
    start = datetime.now(UTC) + timedelta(days=1)
    events = [
        event_crud.create_event(
            db_session, group_id=group.id, title="Scoped", description=None,
            cover_image_url=None, location="Istanbul",
            start_time=start, end_time=start + timedelta(hours=1),
        )
        for group in (own_group, other_group)
    ]
    headers = auth_headers(moderator)
    body = {"title": "Renamed"}

    assert client.put(f"/events/{events[1].id}", json=body, headers=headers).status_code == 403
    assert client.put(f"/events/{events[0].id}", json=body, headers=headers).status_code == 200

    assert client.get(f"/events/{events[0].id}", headers=headers).json()["can_manage"] is True
    assert client.get(f"/events/{events[1].id}", headers=headers).json()["can_manage"] is False
    assert client.get(f"/groups/{own_group.id}", headers=headers).json()["can_create_events"] is True
    assert client.get(f"/groups/{other_group.id}", headers=headers).json()["can_create_events"] is False
    admin_headers = auth_headers(admin)
    assert client.get(f"/events/{events[1].id}", headers=admin_headers).json()["can_manage"] is True
    assert client.get(f"/groups/{other_group.id}", headers=admin_headers).json()["can_create_events"] is True
    user_headers = auth_headers(owner)
    assert client.get(f"/events/{events[0].id}", headers=user_headers).json()["can_manage"] is False
