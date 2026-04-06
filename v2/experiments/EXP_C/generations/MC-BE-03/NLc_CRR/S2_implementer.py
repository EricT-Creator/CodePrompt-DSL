from __future__ import annotations

import json
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel


# ─── Connection State ───

class ConnectionState(Enum):
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"


@dataclass
class Connection:
    websocket: WebSocket
    user_id: str
    nickname: str
    room_id: str
    state: ConnectionState

    def __hash__(self) -> int:
        return hash(self.user_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Connection):
            return False
        return self.user_id == other.user_id


# ─── Message type ───

class Message(BaseModel):
    id: str
    user_id: str
    nickname: str
    content: str
    timestamp: str
    room_id: str


# ─── Room ───

class Room:
    MAX_HISTORY: int = 100

    def __init__(self, room_id: str) -> None:
        self.room_id: str = room_id
        self.connections: set[Connection] = set()
        self.message_history: deque[dict[str, Any]] = deque(maxlen=self.MAX_HISTORY)
        self.created_at: str = datetime.now(timezone.utc).isoformat()

    def add_message(self, message: dict[str, Any]) -> None:
        self.message_history.append(message)

    def get_recent_messages(self, count: int = 50) -> list[dict[str, Any]]:
        messages = list(self.message_history)
        return messages[-count:]

    def get_online_users(self) -> list[dict[str, str]]:
        return [
            {"user_id": conn.user_id, "nickname": conn.nickname}
            for conn in self.connections
            if conn.state == ConnectionState.CONNECTED
        ]


# ─── Room Registry ───

class RoomRegistry:
    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}

    def get_or_create(self, room_id: str) -> Room:
        if room_id not in self._rooms:
            self._rooms[room_id] = Room(room_id)
        return self._rooms[room_id]

    def remove_if_empty(self, room_id: str) -> None:
        if room_id in self._rooms and not self._rooms[room_id].connections:
            del self._rooms[room_id]

    def get_room(self, room_id: str) -> Room | None:
        return self._rooms.get(room_id)

    def list_rooms(self) -> list[dict[str, Any]]:
        return [
            {
                "room_id": r.room_id,
                "online_users": len(r.connections),
                "message_count": len(r.message_history),
                "created_at": r.created_at,
            }
            for r in self._rooms.values()
        ]


# ─── Connection Manager ───

class ConnectionManager:
    def __init__(self, registry: RoomRegistry) -> None:
        self.registry: RoomRegistry = registry
        self._connections: dict[str, Connection] = {}

    async def connect(
        self, websocket: WebSocket, user_id: str, nickname: str, room_id: str
    ) -> Connection:
        await websocket.accept()

        conn = Connection(
            websocket=websocket,
            user_id=user_id,
            nickname=nickname,
            room_id=room_id,
            state=ConnectionState.CONNECTED,
        )

        self._connections[user_id] = conn
        room = self.registry.get_or_create(room_id)
        room.connections.add(conn)

        return conn

    async def disconnect(self, user_id: str) -> str | None:
        if user_id not in self._connections:
            return None

        conn = self._connections[user_id]
        conn.state = ConnectionState.DISCONNECTING
        room_id = conn.room_id

        room = self.registry.get_room(room_id)
        if room:
            room.connections.discard(conn)
            if not room.connections:
                self.registry.remove_if_empty(room_id)

        del self._connections[user_id]
        conn.state = ConnectionState.DISCONNECTED
        return room_id

    async def broadcast_to_room(
        self,
        room_id: str,
        message: dict[str, Any],
        exclude_user: str | None = None,
    ) -> None:
        room = self.registry.get_room(room_id)
        if not room:
            return

        message_json = json.dumps(message)
        disconnected: list[str] = []

        for conn in room.connections:
            if exclude_user and conn.user_id == exclude_user:
                continue
            try:
                await conn.websocket.send_text(message_json)
            except (WebSocketDisconnect, RuntimeError):
                disconnected.append(conn.user_id)
            except Exception:
                disconnected.append(conn.user_id)

        for uid in disconnected:
            await self.disconnect(uid)

    async def broadcast_system_message(self, room_id: str, content: str) -> None:
        message = {
            "type": "system",
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        room = self.registry.get_room(room_id)
        if room:
            room.add_message(message)
        await self.broadcast_to_room(room_id, message)

    async def broadcast_chat_message(
        self,
        room_id: str,
        user_id: str,
        nickname: str,
        content: str,
    ) -> dict[str, Any]:
        msg: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "nickname": nickname,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "room_id": room_id,
        }

        room = self.registry.get_room(room_id)
        if room:
            room.add_message(msg)

        await self.broadcast_to_room(
            room_id,
            {"type": "message", "data": msg},
        )
        return msg

    async def send_history_to_user(self, conn: Connection) -> None:
        room = self.registry.get_room(conn.room_id)
        if not room:
            return
        history = room.get_recent_messages(50)
        try:
            await conn.websocket.send_text(
                json.dumps({"type": "history", "data": history})
            )
        except Exception:
            pass

    async def send_user_list(self, room_id: str) -> None:
        room = self.registry.get_room(room_id)
        if not room:
            return
        users = room.get_online_users()
        await self.broadcast_to_room(
            room_id,
            {"type": "user_list", "data": users},
        )


# ─── Globals ───

room_registry = RoomRegistry()
manager = ConnectionManager(room_registry)


# ─── FastAPI App ───

app = FastAPI(title="WebSocket Chat Server")


# ─── WebSocket endpoint ───

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    user_id: str = Query(...),
    nickname: str = Query("Anonymous"),
) -> None:
    conn = await manager.connect(websocket, user_id, nickname, room_id)

    # Send history
    await manager.send_history_to_user(conn)

    # Notify room
    await manager.broadcast_system_message(room_id, f"{nickname} joined the room")
    await manager.send_user_list(room_id)

    try:
        while conn.state == ConnectionState.CONNECTED:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"type": "error", "content": "Invalid JSON"})
                )
                continue

            msg_type = payload.get("type", "message")
            content = payload.get("content", "")

            if msg_type == "message" and content.strip():
                await manager.broadcast_chat_message(
                    room_id, user_id, nickname, content
                )
            elif msg_type == "typing":
                await manager.broadcast_to_room(
                    room_id,
                    {
                        "type": "typing",
                        "user_id": user_id,
                        "nickname": nickname,
                    },
                    exclude_user=user_id,
                )
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        disconnected_room = await manager.disconnect(user_id)
        if disconnected_room:
            await manager.broadcast_system_message(
                disconnected_room, f"{nickname} left the room"
            )
            await manager.send_user_list(disconnected_room)


# ─── REST endpoints ───

@app.get("/rooms/{room_id}/history")
async def get_room_history(
    room_id: str, limit: int = 50
) -> list[dict[str, Any]]:
    room = room_registry.get_room(room_id)
    if not room:
        return []
    return room.get_recent_messages(limit)


@app.get("/rooms/{room_id}/users")
async def get_room_users(room_id: str) -> list[dict[str, str]]:
    room = room_registry.get_room(room_id)
    if not room:
        return []
    return room.get_online_users()


@app.get("/rooms")
async def list_rooms() -> list[dict[str, Any]]:
    return room_registry.list_rooms()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
