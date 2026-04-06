"""WebSocket Chat Server with multi-room support — FastAPI."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel


# ── Data Structures ──────────────────────────────────────────────────────────


class UserInfo:
    __slots__ = ("nickname", "room_id", "connected_at")

    def __init__(self, nickname: str, room_id: str) -> None:
        self.nickname: str = nickname
        self.room_id: str = room_id
        self.connected_at: str = datetime.now(timezone.utc).isoformat()


class Message:
    __slots__ = ("id", "room_id", "nickname", "content", "timestamp", "type")

    def __init__(
        self,
        room_id: str,
        nickname: str,
        content: str,
        msg_type: str = "user",
    ) -> None:
        self.id: str = str(uuid.uuid4())
        self.room_id: str = room_id
        self.nickname: str = nickname
        self.content: str = content
        self.timestamp: str = datetime.now(timezone.utc).isoformat()
        self.type: str = msg_type

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "room_id": self.room_id,
            "nickname": self.nickname,
            "content": self.content,
            "timestamp": self.timestamp,
            "type": self.type,
        }


# ── Global State ─────────────────────────────────────────────────────────────

rooms: dict[str, set[WebSocket]] = {}
user_info: dict[WebSocket, UserInfo] = {}
message_history: dict[str, list[dict[str, Any]]] = {}


# ── Broadcast ────────────────────────────────────────────────────────────────


async def broadcast(room_id: str, message: Message) -> None:
    msg_dict = message.to_dict()

    # Store in history
    history = message_history.setdefault(room_id, [])
    history.append(msg_dict)
    if len(history) > 100:
        history.pop(0)

    # Broadcast to all connections in the room
    stale: set[WebSocket] = set()
    for ws in rooms.get(room_id, set()):
        try:
            await ws.send_json(msg_dict)
        except Exception:
            stale.add(ws)

    # Clean up stale connections
    for ws in stale:
        rooms.get(room_id, set()).discard(ws)
        user_info.pop(ws, None)


# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="WebSocket Chat Server")


# ── WebSocket Endpoint ───────────────────────────────────────────────────────


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    nickname: str = Query(default="Anonymous"),
) -> None:
    await websocket.accept()

    # Register connection
    rooms.setdefault(room_id, set()).add(websocket)
    info = UserInfo(nickname=nickname, room_id=room_id)
    user_info[websocket] = info

    # Broadcast join message
    join_msg = Message(
        room_id=room_id,
        nickname="system",
        content=f"{nickname} has joined the room.",
        msg_type="system",
    )
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

            user_msg = Message(
                room_id=room_id,
                nickname=nickname,
                content=content,
                msg_type="user",
            )
            await broadcast(room_id, user_msg)

    except WebSocketDisconnect:
        pass
    finally:
        # Remove connection
        rooms.get(room_id, set()).discard(websocket)
        user_info.pop(websocket, None)

        # Broadcast leave message
        leave_msg = Message(
            room_id=room_id,
            nickname="system",
            content=f"{nickname} has left the room.",
            msg_type="system",
        )
        await broadcast(room_id, leave_msg)

        # Clean up empty room
        if room_id in rooms and len(rooms[room_id]) == 0:
            del rooms[room_id]
            message_history.pop(room_id, None)


# ── REST Endpoints ───────────────────────────────────────────────────────────


class RoomInfo(BaseModel):
    room_id: str
    online_count: int
    users: list[str]


@app.get("/rooms", response_model=list[RoomInfo])
async def list_rooms() -> list[RoomInfo]:
    results: list[RoomInfo] = []
    for rid, connections in rooms.items():
        if not connections:
            continue
        users_list: list[str] = []
        for ws in connections:
            info = user_info.get(ws)
            if info:
                users_list.append(info.nickname)
        results.append(
            RoomInfo(
                room_id=rid,
                online_count=len(connections),
                users=users_list,
            )
        )
    return results


@app.get("/rooms/{room_id}/users", response_model=list[str])
async def get_room_users(room_id: str) -> list[str]:
    connections = rooms.get(room_id, set())
    users_list: list[str] = []
    for ws in connections:
        info = user_info.get(ws)
        if info:
            users_list.append(info.nickname)
    return users_list


@app.get("/rooms/{room_id}/history")
async def get_room_history(room_id: str) -> list[dict[str, Any]]:
    return message_history.get(room_id, [])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
