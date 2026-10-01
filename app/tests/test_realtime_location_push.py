import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.routes.chat_ws import websocket_chat
from app.api.routes.chats import list_chats
from app.services.location_discovery import nearby_events
from app.services.push_dispatcher import NotificationDispatcher


def test_websocket_rejects_missing_token():
    socket = SimpleNamespace(query_params={}, headers={})

    async def record_close(**kwargs):
        socket.closed_with = kwargs

    socket.close = record_close
    asyncio.run(websocket_chat(socket))
    assert socket.closed_with["code"] == 1008


def test_resume_rejects_cursor_from_another_room():
    group_id, other_group_id = uuid4(), uuid4()
    user = SimpleNamespace(id=uuid4())
    with patch("app.api.routes.chats.resolve_chat_context", return_value=(group_id, None)), \
         patch("app.api.routes.chats.chat_crud.get_chat", return_value=SimpleNamespace(group_id=other_group_id, event_id=None)):
        with pytest.raises(HTTPException) as error:
            list_chats(Mock(), user, group_id=group_id, event_id=None, limit=100, after_id=uuid4())
    assert error.value.status_code == 400


def test_nearby_query_rounds_distance_and_hides_coordinates():
    event = SimpleNamespace(id=uuid4(), title="Konser", description=None,
        start_time=datetime.now(UTC), location="İstanbul", city="İstanbul", group_id=uuid4())
    db = Mock()
    db.execute.return_value.all.return_value = [(event, 1.49)]
    result = nearby_events(db, lat=41.0, lon=29.0, radius_km=25)
    assert result[0]["distance_km"] == 1
    assert "latitude" not in result[0] and "longitude" not in result[0]


def test_notification_dispatcher_skips_disabled_preference():
    sender = Mock()
    db = Mock()
    db.get.return_value = SimpleNamespace(enabled=False)
    NotificationDispatcher(sender).dispatch(db, user_ids=[uuid4()], category="event",
                                            title="Etkinlik", message="Yeni etkinlik")
    db.add.assert_not_called()
    sender.send.assert_not_called()


def test_notification_dispatcher_catches_sender_failure():
    sender = Mock()
    sender.send.side_effect = RuntimeError("push gateway unavailable")
    db = Mock()
    db.get.return_value = None
    db.scalars.return_value.all.return_value = [SimpleNamespace(id=uuid4())]
    NotificationDispatcher(sender).dispatch(db, user_ids=[uuid4()], category="group",
                                            title="Grup", message="Yeni grup")
    db.add.assert_called_once()
    db.commit.assert_called_once()
    sender.send.assert_called_once()
