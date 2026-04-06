"""WebSocket Chat Server — MC-BE-03 (H × RRC, S2 Implementer)"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

# ─── Connection Manager ───


class ConnectionManager:
    def __init__(self) -> None:
        self.rooms: dict[str, set[tuple[str, WebSocket]]] = {}
        self.history: dict[str, list[dict[str, Any]]] = {}
        self._max_history: int = 100

    def connect(self, room_id: str, nickname: str, ws: WebSocket) -> bool:
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
            self.history[room_id] = []

        # Check nickname uniqueness within room
        for nick, _ in self.rooms[room_id]:
            if nick == nickname:
                return False

        self.rooms[room_id].add((nickname, ws))
        return True

    def disconnect(self, room_id: str, nickname: str) -> None:
        if room_id not in self.rooms:
            return
        to_remove: tuple[str, WebSocket] | None = None
        for entry in self.rooms[room_id]:
            if entry[0] == nickname:
                to_remove = entry
                break
        if to_remove:
            self.rooms[room_id].discard(to_remove)
        # Optional: clean up empty rooms
        if room_id in self.rooms and len(self.rooms[room_id]) == 0:
            del self.rooms[room_id]

    async def broadcast(self, room_id: str, message: dict[str, Any]) -> None:
        if room_id not in self.rooms:
            return
        dead_connections: list[tuple[str, WebSocket]] = []
        for nickname, ws in self.rooms[room_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead_connections.append((nickname, ws))
        for conn in dead_connections:
            self.rooms[room_id].discard(conn)

    def store_message(self, room_id: str, message: dict[str, Any]) -> None:
        if room_id not in self.history:
            self.history[room_id] = []
        history = self.history[room_id]
        history.append(message)
        if len(history) > self._max_history:
            self.history[room_id] = history[-self._max_history :]

    def get_history(self, room_id: str) -> list[dict[str, Any]]:
        return list(self.history.get(room_id, []))

    def get_online_users(self, room_id: str) -> list[str]:
        if room_id not in self.rooms:
            return []
        return [nick for nick, _ in self.rooms[room_id]]


# ─── Message helpers ───


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_message(nickname: str, text: str) -> dict[str, Any]:
    return {
        "type": "message",
        "nickname": nickname,
        "text": text,
        "timestamp": _now_iso(),
    }


def system_msg(text: str) -> dict[str, Any]:
    return {
        "type": "system",
        "nickname": "system",
        "text": text,
        "timestamp": _now_iso(),
    }


# ─── Response Models ───


class RoomUsersResponse(BaseModel):
    room_id: str
    users: list[str]
    count: int


# ─── Application ───

app = FastAPI(title="WebSocket Chat Server")
manager = ConnectionManager()


@app.websocket("/ws/{room_id}/{nickname}")
async def websocket_endpoint(ws: WebSocket, room_id: str, nickname: str) -> None:
    await ws.accept()

    if not manager.connect(room_id, nickname, ws):
        await ws.send_json({"type": "error", "text": "Nickname already taken"})
        await ws.close(code=4001, reason="Nickname already taken")
        return

    try:
        # Send history
        for msg in manager.get_history(room_id):
            await ws.send_json(msg)

        # Broadcast join
        join_msg = system_msg(f"{nickname} joined")
        manager.store_message(room_id, join_msg)
        await manager.broadcast(room_id, join_msg)

        # Message loop
        while True:
            try:
                data = await ws.receive_json()
            except Exception:
                # Malformed JSON — ignore and keep connection open
                continue

            text = data.get("text", "")
            if not isinstance(text, str) or not text.strip():
                continue

            message = build_message(nickname, text.strip())
            manager.store_message(room_id, message)
            await manager.broadcast(room_id, message)

    except WebSocketDisconnect:
        manager.disconnect(room_id, nickname)
        leave_msg = system_msg(f"{nickname} left")
        manager.store_message(room_id, leave_msg)
        await manager.broadcast(room_id, leave_msg)


@app.get("/rooms/{room_id}/users", response_model=RoomUsersResponse)
async def get_room_users(room_id: str) -> RoomUsersResponse:
    users = manager.get_online_users(room_id)
    return RoomUsersResponse(room_id=room_id, users=users, count=len(users))
