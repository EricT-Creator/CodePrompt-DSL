"""WebSocket Chat Server — FastAPI implementation with multi-room support."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel


# ─── Data Structures ──────────────────────────────────────────


class UserInfo:
    __slots__ = ("nickname", "room_id", "connected_at")

    def __init__(self, nickname: str, room_id: str) -> None:
        self.nickname = nickname
        self.room_id = room_id
        self.connected_at = datetime.now(timezone.utc).isoformat()


class Message:
    __slots__ = ("id", "room_id", "nickname", "content", "timestamp", "type")

    def __init__(
        self,
        room_id: str,
        nickname: str,
        content: str,
        msg_type: str = "user",
    ) -> None:
        self.id = str(uuid.uuid4())
        self.room_id = room_id
        self.nickname = nickname
        self.content = content
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.type = msg_type

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "room_id": self.room_id,
            "nickname": self.nickname,
            "content": self.content,
            "timestamp": self.timestamp,
            "type": self.type,
        }


# Global state
rooms: dict[str, set[WebSocket]] = {}
user_info: dict[WebSocket, UserInfo] = {}
message_history: dict[str, list[Message]] = {}

MAX_HISTORY = 100


# ─── Broadcast ────────────────────────────────────────────────


async def broadcast(room_id: str, message: Message) -> None:
    stale: set[WebSocket] = set()
    for ws in rooms.get(room_id, set()):
        try:
            await ws.send_json(message.to_dict())
        except Exception:
            stale.add(ws)
    for ws in stale:
        rooms.get(room_id, set()).discard(ws)
        user_info.pop(ws, None)


def store_message(room_id: str, message: Message) -> None:
    history = message_history.setdefault(room_id, [])
    history.append(message)
    if len(history) > MAX_HISTORY:
        history.pop(0)


# ─── Response Models ──────────────────────────────────────────


class RoomInfo(BaseModel):
    room_id: str
    online_count: int
    users: list[str]


class MessageResponse(BaseModel):
    id: str
    room_id: str
    nickname: str
    content: str
    timestamp: str
    type: str


# ─── App ──────────────────────────────────────────────────────

app = FastAPI(title="WebSocket Chat Server")


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    nickname: str = Query(default="Anonymous"),
) -> None:
    await websocket.accept()

    # Register user
    if room_id not in rooms:
        rooms[room_id] = set()
        message_history.setdefault(room_id, [])

    rooms[room_id].add(websocket)
    info = UserInfo(nickname=nickname, room_id=room_id)
    user_info[websocket] = info

    # Broadcast join message
    join_msg = Message(
        room_id=room_id,
        nickname="system",
        content=f"{nickname} has joined the room",
        msg_type="system",
    )
    store_message(room_id, join_msg)
    await broadcast(room_id, join_msg)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = __import__("json").loads(raw)
                content = data.get("content", "")
            except (ValueError, AttributeError):
                content = raw

            if not content:
                continue

            msg = Message(
                room_id=room_id,
                nickname=nickname,
                content=content,
                msg_type="user",
            )
            store_message(room_id, msg)
            await broadcast(room_id, msg)

    except WebSocketDisconnect:
        pass
    finally:
        # Cleanup
        rooms.get(room_id, set()).discard(websocket)
        user_info.pop(websocket, None)

        leave_msg = Message(
            room_id=room_id,
            nickname="system",
            content=f"{nickname} has left the room",
            msg_type="system",
        )
        store_message(room_id, leave_msg)
        await broadcast(room_id, leave_msg)

        # Clean up empty rooms
        if room_id in rooms and len(rooms[room_id]) == 0:
            del rooms[room_id]
            message_history.pop(room_id, None)


@app.get("/rooms", response_model=list[RoomInfo])
async def list_rooms() -> list[RoomInfo]:
    result: list[RoomInfo] = []
    for room_id, connections in rooms.items():
        users = []
        for ws in connections:
            info = user_info.get(ws)
            if info:
                users.append(info.nickname)
        result.append(RoomInfo(room_id=room_id, online_count=len(connections), users=users))
    return result


@app.get("/rooms/{room_id}/users", response_model=list[str])
async def list_room_users(room_id: str) -> list[str]:
    connections = rooms.get(room_id, set())
    users = []
    for ws in connections:
        info = user_info.get(ws)
        if info:
            users.append(info.nickname)
    return users


@app.get("/rooms/{room_id}/history", response_model=list[MessageResponse])
async def get_room_history(room_id: str) -> list[MessageResponse]:
    history = message_history.get(room_id, [])
    return [
        MessageResponse(**msg.to_dict())
        for msg in history
    ]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
