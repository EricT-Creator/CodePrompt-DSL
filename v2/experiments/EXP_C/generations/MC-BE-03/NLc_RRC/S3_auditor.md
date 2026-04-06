# MC-BE-03 Code Review Report (NLc_RRC)

## Constraint Review

- C1 (Python + FastAPI): PASS — Uses Python with FastAPI framework (line 2234)
- C2 (Set iteration broadcast, no async queue): PASS — Broadcast uses set iteration via `room.connections.keys()` (lines 2361-2369), no asyncio.Queue used for broadcasting
- C3 (fastapi + uvicorn only): FAIL — Uses `pydantic` (line 2235) which is a third-party package, not allowed
- C4 (Single file): PASS — All code delivered in a single Python file
- C5 (Message history list ≤100): PASS — Message history uses `deque(maxlen=100)` (line 2275), automatically caps at 100 messages
- C6 (Code only): PASS — Output contains code only, no explanation text

## Functionality Assessment (0-5)
Score: 4 — The code correctly implements WebSocket chat server with set-based broadcasting and capped message history using deque. However, it violates C3 by using pydantic which is not allowed.

## Corrected Code

```py
import json
import time
from collections import deque
from dataclasses import dataclass, asdict
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query


# ─── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class ChatMessage:
    nickname: str
    content: str
    timestamp: str
    msg_type: str  # "user" | "system"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class UserInfo:
    nickname: str


# ─── Room ─────────────────────────────────────────────────────────────────────

class Room:
    def __init__(self) -> None:
        self.connections: dict[WebSocket, str] = {}
        self.history: deque[ChatMessage] = deque(maxlen=100)

    def add_connection(self, ws: WebSocket, nickname: str) -> None:
        self.connections[ws] = nickname

    def remove_connection(self, ws: WebSocket) -> str | None:
        return self.connections.pop(ws, None)

    def get_nicknames(self) -> list[str]:
        return list(self.connections.values())

    def add_message(self, msg: ChatMessage) -> None:
        self.history.append(msg)

    def get_history(self) -> list[dict[str, Any]]:
        return [m.to_dict() for m in self.history]


# ─── Room Manager ─────────────────────────────────────────────────────────────

class RoomManager:
    def __init__(self) -> None:
        self.rooms: dict[str, Room] = {}

    def get_or_create_room(self, room_id: str) -> Room:
        if room_id not in self.rooms:
            self.rooms[room_id] = Room()
        return self.rooms[room_id]

    def get_room(self, room_id: str) -> Room | None:
        return self.rooms.get(room_id)

    def list_rooms(self) -> list[str]:
        return [rid for rid, room in self.rooms.items() if len(room.connections) > 0]

    async def join(self, room_id: str, ws: WebSocket, nickname: str) -> None:
        room = self.get_or_create_room(room_id)
        room.add_connection(ws, nickname)

        system_msg = ChatMessage(
            nickname="system",
            content=f"{nickname} has joined the room",
            timestamp=_now_iso(),
            msg_type="system",
        )
        room.add_message(system_msg)

        history = room.get_history()
        await ws.send_text(json.dumps({"type": "history", "messages": history}))

        await self._broadcast(room, system_msg, exclude=ws)

    async def leave(self, room_id: str, ws: WebSocket) -> None:
        room = self.get_room(room_id)
        if room is None:
            return
        nickname = room.remove_connection(ws)
        if nickname is None:
            return

        system_msg = ChatMessage(
            nickname="system",
            content=f"{nickname} has left the room",
            timestamp=_now_iso(),
            msg_type="system",
        )
        room.add_message(system_msg)
        await self._broadcast(room, system_msg, exclude=None)

    async def broadcast_message(self, room_id: str, ws: WebSocket, content: str) -> None:
        room = self.get_room(room_id)
        if room is None:
            return
        nickname = room.connections.get(ws, "unknown")
        msg = ChatMessage(
            nickname=nickname,
            content=content,
            timestamp=_now_iso(),
            msg_type="user",
        )
        room.add_message(msg)
        await self._broadcast(room, msg, exclude=ws)

    async def _broadcast(self, room: Room, msg: ChatMessage, exclude: WebSocket | None) -> None:
        payload = json.dumps({"type": "message", "data": msg.to_dict()})
        disconnected: list[WebSocket] = []
        for conn in list(room.connections.keys()):
            if conn is exclude:
                continue
            try:
                await conn.send_text(payload)
            except Exception:
                disconnected.append(conn)
        for conn in disconnected:
            room.remove_connection(conn)

    def get_users(self, room_id: str) -> list[str]:
        room = self.get_room(room_id)
        if room is None:
            return []
        return room.get_nicknames()

    def get_history(self, room_id: str) -> list[dict[str, Any]]:
        room = self.get_room(room_id)
        if room is None:
            return []
        return room.get_history()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ─── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(title="WebSocket Chat Server")
manager = RoomManager()


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    nickname: str = Query(...),
) -> None:
    await websocket.accept()
    await manager.join(room_id, websocket, nickname)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast_message(room_id, websocket, data)
    except WebSocketDisconnect:
        await manager.leave(room_id, websocket)


@app.get("/rooms/{room_id}/users")
async def get_room_users(room_id: str) -> list[str]:
    return manager.get_users(room_id)


@app.get("/rooms/{room_id}/history")
async def get_room_history(room_id: str) -> list[dict[str, Any]]:
    return manager.get_history(room_id)


@app.get("/rooms")
async def list_rooms() -> list[str]:
    return manager.list_rooms()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```
