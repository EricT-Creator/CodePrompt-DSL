"""WebSocket Chat Server — MC-BE-03 (H × RRS)"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

# ─── Message helpers ───

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_message(nickname: str, text: str) -> dict[str, str]:
    return {
        "type": "message",
        "nickname": nickname,
        "text": text,
        "timestamp": _now_iso(),
    }


def system_msg(text: str) -> dict[str, str]:
    return {
        "type": "system",
        "nickname": "system",
        "text": text,
        "timestamp": _now_iso(),
    }


# ─── Connection Manager ───

class ConnectionManager:
    MAX_HISTORY: int = 100

    def __init__(self) -> None:
        self.rooms: dict[str, set[tuple[str, WebSocket]]] = {}
        self.history: dict[str, list[dict[str, str]]] = {}

    def _ensure_room(self, room_id: str) -> None:
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
        if room_id not in self.history:
            self.history[room_id] = []

    def nickname_taken(self, room_id: str, nickname: str) -> bool:
        if room_id not in self.rooms:
            return False
        for nick, _ in self.rooms[room_id]:
            if nick == nickname:
                return True
        return False

    def connect(self, room_id: str, nickname: str, ws: WebSocket) -> None:
        self._ensure_room(room_id)
        self.rooms[room_id].add((nickname, ws))

    def disconnect(self, room_id: str, nickname: str) -> None:
        if room_id not in self.rooms:
            return
        to_remove: tuple[str, WebSocket] | None = None
        for item in self.rooms[room_id]:
            if item[0] == nickname:
                to_remove = item
                break
        if to_remove:
            self.rooms[room_id].discard(to_remove)

    def get_history(self, room_id: str) -> list[dict[str, str]]:
        return self.history.get(room_id, [])

    def store_message(self, room_id: str, message: dict[str, str]) -> None:
        self._ensure_room(room_id)
        history = self.history[room_id]
        history.append(message)
        if len(history) > self.MAX_HISTORY:
            self.history[room_id] = history[-self.MAX_HISTORY:]

    async def broadcast(self, room_id: str, message: dict[str, str]) -> None:
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

    def get_online_users(self, room_id: str) -> list[str]:
        if room_id not in self.rooms:
            return []
        return [nick for nick, _ in self.rooms[room_id]]


# ─── App ───

app = FastAPI(title="WebSocket Chat Server")
manager = ConnectionManager()


# ─── WebSocket endpoint ───

@app.websocket("/ws/{room_id}/{nickname}")
async def websocket_endpoint(ws: WebSocket, room_id: str, nickname: str) -> None:
    # Check nickname uniqueness
    if manager.nickname_taken(room_id, nickname):
        await ws.close(code=4001, reason="Nickname already taken")
        return

    await ws.accept()
    manager.connect(room_id, nickname, ws)

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
                data: dict[str, Any] = await ws.receive_json()
            except ValueError:
                # Malformed JSON — ignore, keep connection open
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


# ─── REST endpoints ───

class RoomUsersResponse(BaseModel):
    room_id: str
    users: list[str]
    count: int


@app.get("/rooms/{room_id}/users", response_model=RoomUsersResponse)
async def get_room_users(room_id: str) -> RoomUsersResponse:
    users = manager.get_online_users(room_id)
    return RoomUsersResponse(room_id=room_id, users=users, count=len(users))
