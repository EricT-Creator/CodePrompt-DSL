import json
import time
from collections import deque
from dataclasses import dataclass, asdict
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel


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


class UserInfo(BaseModel):
    nickname: str


class RoomInfo(BaseModel):
    room_id: str
    user_count: int


class MessageInfo(BaseModel):
    nickname: str
    content: str
    timestamp: str
    msg_type: str


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


@app.get("/rooms/{room_id}/users", response_model=list[str])
async def get_room_users(room_id: str) -> list[str]:
    return manager.get_users(room_id)


@app.get("/rooms/{room_id}/history", response_model=list[MessageInfo])
async def get_room_history(room_id: str) -> list[dict[str, Any]]:
    return manager.get_history(room_id)


@app.get("/rooms", response_model=list[str])
async def list_rooms() -> list[str]:
    return manager.list_rooms()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
