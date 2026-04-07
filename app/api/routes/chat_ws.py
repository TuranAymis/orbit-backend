from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError

from app.api.deps import get_current_user_from_raw_token
from app.core.database import SessionLocal
from app.core.exceptions import AppException
from app.crud import chat as chat_crud
from app.models.user import User
from app.schemas.chat import (
    ChatRead,
    ChatSocketAck,
    ChatSocketRoomPayload,
    ChatSocketSendPayload,
    ChatSocketSyncPayload,
)
from app.services.chat_realtime import SocketIdentity, chat_connection_manager
from app.services.chat_service import build_room_name, persist_chat_message, resolve_chat_context, to_chat_read


router = APIRouter(tags=["ChatRealtime"])


def _extract_socket_token(websocket: WebSocket) -> str | None:
    query_token = websocket.query_params.get("token") or websocket.query_params.get("access_token")
    if query_token:
        return query_token

    authorization = websocket.headers.get("authorization")
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:]

    return None

async def _send_ack(
    websocket: WebSocket,
    *,
    request_id: str | None,
    success: bool,
    message: ChatRead | None = None,
    error: str | None = None,
) -> None:
    payload = ChatSocketAck(success=success, message=message, error=error).model_dump(
        mode="json"
    )
    await chat_connection_manager.send_event(
        websocket,
        event="chat:ack",
        request_id=request_id,
        data=payload,
    )


async def _handle_join(
    websocket: WebSocket,
    *,
    current_user: User,
    request_id: str | None,
    payload: dict,
) -> None:
    room_payload = ChatSocketRoomPayload.model_validate(payload)
    with SessionLocal() as db:
        db_user = db.get(User, current_user.id)
        group_id, event_id = resolve_chat_context(
            db,
            current_user=db_user,
            group_id=room_payload.group_id,
            event_id=room_payload.event_id,
        )
    room_name = build_room_name(group_id=group_id, event_id=event_id)
    await chat_connection_manager.join_room(websocket, room_name=room_name)
    await chat_connection_manager.send_event(
        websocket,
        event="chat:joined",
        request_id=request_id,
        data={
            "success": True,
            "room": room_name,
            "group_id": str(group_id) if group_id else None,
            "event_id": str(event_id) if event_id else None,
        },
    )


async def _handle_leave(
    websocket: WebSocket,
    *,
    current_user: User,
    request_id: str | None,
    payload: dict,
) -> None:
    room_payload = ChatSocketRoomPayload.model_validate(payload)
    with SessionLocal() as db:
        db_user = db.get(User, current_user.id)
        group_id, event_id = resolve_chat_context(
            db,
            current_user=db_user,
            group_id=room_payload.group_id,
            event_id=room_payload.event_id,
        )
    room_name = build_room_name(group_id=group_id, event_id=event_id)
    await chat_connection_manager.leave_room(websocket, room_name=room_name)
    await chat_connection_manager.send_event(
        websocket,
        event="chat:left",
        request_id=request_id,
        data={
            "success": True,
            "room": room_name,
            "group_id": str(group_id) if group_id else None,
            "event_id": str(event_id) if event_id else None,
        },
    )


async def _handle_send(
    websocket: WebSocket,
    *,
    current_user: User,
    request_id: str | None,
    payload: dict,
) -> None:
    send_payload = ChatSocketSendPayload.model_validate(payload)
    with SessionLocal() as db:
        db_user = db.get(User, current_user.id)
        group_id, event_id = resolve_chat_context(
            db,
            current_user=db_user,
            group_id=send_payload.group_id,
            event_id=send_payload.event_id,
        )
        message = persist_chat_message(
            db,
            current_user=db_user,
            group_id=group_id,
            event_id=event_id,
            content=send_payload.content,
        )

    await _send_ack(
        websocket,
        request_id=request_id,
        success=True,
        message=message,
    )
    room_name = build_room_name(group_id=message.group_id, event_id=message.event_id)
    await chat_connection_manager.broadcast(
        room_name=room_name,
        event="chat:message",
        data=message.model_dump(mode="json"),
    )


async def _handle_sync(
    websocket: WebSocket,
    *,
    current_user: User,
    request_id: str | None,
    payload: dict,
) -> None:
    sync_payload = ChatSocketSyncPayload.model_validate(payload)
    with SessionLocal() as db:
        db_user = db.get(User, current_user.id)
        group_id, event_id = resolve_chat_context(
            db,
            current_user=db_user,
            group_id=sync_payload.group_id,
            event_id=sync_payload.event_id,
        )
        chats = chat_crud.list_chats_since(
            db,
            group_id=group_id,
            event_id=event_id,
            after_chat_id=sync_payload.last_seen_message_id,
            after_created_at=sync_payload.last_seen_created_at,
        )
        messages = [to_chat_read(chat).model_dump(mode="json") for chat in chats]

    await chat_connection_manager.send_event(
        websocket,
        event="chat:sync",
        request_id=request_id,
        data={
            "success": True,
            "group_id": str(group_id) if group_id else None,
            "event_id": str(event_id) if event_id else None,
            "messages": messages,
        },
    )


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    token = _extract_socket_token(websocket)
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Not authenticated")
        return

    with SessionLocal() as db:
        try:
            current_user = get_current_user_from_raw_token(db, token)
        except AppException as exc:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason=exc.detail,
            )
            return

    await chat_connection_manager.connect(
        websocket,
        identity=SocketIdentity(user_id=current_user.id, email=current_user.email),
    )
    await chat_connection_manager.send_event(
        websocket,
        event="chat:connected",
        data={"success": True, "user_id": str(current_user.id)},
    )

    try:
        while True:
            message = await websocket.receive_json()
            event = message.get("event")
            payload = message.get("data", {})
            request_id = message.get("request_id")

            try:
                if event == "chat:join":
                    await _handle_join(
                        websocket,
                        current_user=current_user,
                        request_id=request_id,
                        payload=payload,
                    )
                elif event == "chat:leave":
                    await _handle_leave(
                        websocket,
                        current_user=current_user,
                        request_id=request_id,
                        payload=payload,
                    )
                elif event == "chat:send":
                    await _handle_send(
                        websocket,
                        current_user=current_user,
                        request_id=request_id,
                        payload=payload,
                    )
                elif event == "chat:sync":
                    await _handle_sync(
                        websocket,
                        current_user=current_user,
                        request_id=request_id,
                        payload=payload,
                    )
                else:
                    await _send_ack(
                        websocket,
                        request_id=request_id,
                        success=False,
                        error="Unsupported event.",
                    )
            except (ValidationError, AppException, ValueError) as exc:
                error_message = exc.errors()[0]["msg"] if isinstance(exc, ValidationError) else str(exc)
                await _send_ack(
                    websocket,
                    request_id=request_id,
                    success=False,
                    error=error_message,
                )
    except WebSocketDisconnect:
        await chat_connection_manager.disconnect(websocket)
