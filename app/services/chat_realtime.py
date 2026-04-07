from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from fastapi import WebSocket


@dataclass(frozen=True)
class SocketIdentity:
    user_id: UUID
    email: str


class ChatConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self._socket_rooms: dict[WebSocket, set[str]] = defaultdict(set)
        self._socket_identities: dict[WebSocket, SocketIdentity] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, *, identity: SocketIdentity) -> None:
        await websocket.accept()
        async with self._lock:
            self._socket_identities[websocket] = identity

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            room_names = list(self._socket_rooms.pop(websocket, set()))
            for room_name in room_names:
                self._rooms[room_name].discard(websocket)
                if not self._rooms[room_name]:
                    self._rooms.pop(room_name, None)
            self._socket_identities.pop(websocket, None)

    async def join_room(self, websocket: WebSocket, *, room_name: str) -> None:
        async with self._lock:
            self._rooms[room_name].add(websocket)
            self._socket_rooms[websocket].add(room_name)

    async def leave_room(self, websocket: WebSocket, *, room_name: str) -> None:
        async with self._lock:
            self._rooms[room_name].discard(websocket)
            if not self._rooms[room_name]:
                self._rooms.pop(room_name, None)
            self._socket_rooms[websocket].discard(room_name)
            if not self._socket_rooms[websocket]:
                self._socket_rooms.pop(websocket, None)

    async def send_event(
        self,
        websocket: WebSocket,
        *,
        event: str,
        data: dict,
        request_id: str | None = None,
    ) -> None:
        await websocket.send_json(
            {
                "event": event,
                "request_id": request_id,
                "data": data,
            }
        )

    async def broadcast(
        self,
        *,
        room_name: str,
        event: str,
        data: dict,
    ) -> None:
        async with self._lock:
            recipients = list(self._rooms.get(room_name, set()))

        stale_connections: list[WebSocket] = []
        for websocket in recipients:
            try:
                await websocket.send_json(
                    {
                        "event": event,
                        "data": data,
                    }
                )
            except Exception:
                stale_connections.append(websocket)

        for websocket in stale_connections:
            await self.disconnect(websocket)


chat_connection_manager = ChatConnectionManager()
