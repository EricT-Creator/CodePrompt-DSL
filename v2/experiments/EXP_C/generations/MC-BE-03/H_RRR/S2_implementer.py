"""WebSocket Chat Server — MC-BE-03 (H × RRR)"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

# ── Message Helpers ──
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def system_msg(text: str) -> dict[str, str]:
    return {
        "type": "system",
        "nickname": "system",
        "text": text,
        "timestamp": now_iso(),
    }

def build_message(nickname: str, text: str) -> dict[str, str]:
    return {
        "type": "message",
        "nickname": nickname,
        "text": text,
        "timestamp": now_iso(),
    }

# ── Connection Manager ──
class ConnectionManager:
    def __init__(self) -> None:
        self.rooms: dict[str, set[tuple[str, WebSocket]]] = {}
        self.history: dict[str, list[dict[str, str]]] = {}

    def connect(self, room_id: str, nickname: str, ws: WebSocket) -> None:
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
        if room_id not in self.history:
            self.history[room_id] = []

        # Check nickname uniqueness
        for nick, _ in self.rooms[room_id]:
            if nick == nickname:
                raise ValueError(f"Nickname '{nickname}' already taken in room '{room_id}'")

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
        # Optional: clean up empty rooms
        if room_id in self.rooms and len(self.rooms[room_id]) == 0:
            del self.rooms[room_id]

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

    def store_message(self, room_id: str, message: dict[str, str]) -> None:
        if room_id not in self.history:
            self.history[room_id] = []
        self.history[room_id].append(message)
        if len(self.history[room_id]) > 100:
            self.history[room_id] = self.history[room_id][-100:]

    def get_history(self, room_id: str) -> list[dict[str, str]]:
        return self.history.get(room_id, [])

    def get_online_users(self, room_id: str) -> list[str]:
        if room_id not in self.rooms:
            return []
        return [nick for nick, _ in self.rooms[room_id]]

# ── Pydantic Models ──
class RoomUsersResponse(BaseModel):
    room_id: str
    users: list[str]
    count: int

# ── Application ──
app = FastAPI(title="WebSocket Chat Server")
manager = ConnectionManager()

# ── WebSocket Endpoint ──
@app.websocket("/ws/{room_id}/{nickname}")
async def websocket_endpoint(ws: WebSocket, room_id: str, nickname: str) -> None:
    await ws.accept()

    # Check nickname uniqueness
    try:
        manager.connect(room_id, nickname, ws)
    except ValueError:
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
                # Malformed JSON — ignore, keep connection open
                continue

            text = data.get("text", "")
            if not text:
                continue

            message = build_message(nickname, text)
            manager.store_message(room_id, message)
            await manager.broadcast(room_id, message)

    except WebSocketDisconnect:
        manager.disconnect(room_id, nickname)
        leave_msg = system_msg(f"{nickname} left")
        manager.store_message(room_id, leave_msg)
        await manager.broadcast(room_id, leave_msg)

# ── REST Endpoint ──
@app.get("/rooms/{room_id}/users", response_model=RoomUsersResponse)
async def get_room_users(room_id: str) -> RoomUsersResponse:
    users = manager.get_online_users(room_id)
    return RoomUsersResponse(
        room_id=room_id,
        users=users,
        count=len(users),
    )
