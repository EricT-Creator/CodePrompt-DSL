import json
import time
from collections import deque
from dataclasses import dataclass, asdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel


# ── Data Models ──

@dataclass
class ChatMessage:
    nickname: str
    content: str
    timestamp: str
    msg_type: str  # "user" | "system"


class Room:
    def __init__(self) -> None:
        self.connections: dict[WebSocket, str] = {}
        self.history: deque[ChatMessage] = deque(maxlen=100)


# ── Room Manager ──

class RoomManager:
    def __init__(self) -> None:
        self.rooms: dict[str, Room] = {}

    def _get_or_create_room(self, room_id: str) -> Room:
        if room_id not in self.rooms:
            self.rooms[room_id] = Room()
        return self.rooms[room_id]

    async def join(self, room_id: str, ws: WebSocket, nickname: str) -> None:
        room = self._get_or_create_room(room_id)
        room.connections[ws] = nickname

        history_data = [asdict(msg) for msg in room.history]
        await ws.send_text(json.dumps({"type": "history", "messages": history_data}))

        system_msg = ChatMessage(
            nickname="system",
            content=f"{nickname} joined the room",
            timestamp=self._timestamp(),
            msg_type="system",
        )
        room.history.append(system_msg)
        await self._broadcast(room_id, system_msg, exclude=None)

    async def leave(self, room_id: str, ws: WebSocket) -> None:
        room = self.rooms.get(room_id)
        if room is None:
            return

        nickname = room.connections.pop(ws, None)
        if nickname is None:
            return

        system_msg = ChatMessage(
            nickname="system",
            content=f"{nickname} left the room",
            timestamp=self._timestamp(),
            msg_type="system",
        )
        room.history.append(system_msg)
        await self._broadcast(room_id, system_msg, exclude=None)

    async def broadcast_message(self, room_id: str, ws: WebSocket, content: str) -> None:
        room = self.rooms.get(room_id)
        if room is None:
            return

        nickname = room.connections.get(ws, "unknown")
        msg = ChatMessage(
            nickname=nickname,
            content=content,
            timestamp=self._timestamp(),
            msg_type="user",
        )
        room.history.append(msg)
        await self._broadcast(room_id, msg, exclude=ws)

    async def _broadcast(self, room_id: str, message: ChatMessage, exclude: WebSocket | None) -> None:
        room = self.rooms.get(room_id)
        if room is None:
            return

        data = json.dumps({"type": "message", "data": asdict(message)})
        disconnected: list[WebSocket] = []

        for conn in list(room.connections.keys()):
            if conn is exclude:
                continue
            try:
                await conn.send_text(data)
            except (RuntimeError, Exception):
                disconnected.append(conn)

        for conn in disconnected:
            room.connections.pop(conn, None)

    def get_users(self, room_id: str) -> list[str]:
        room = self.rooms.get(room_id)
        if room is None:
            return []
        return list(room.connections.values())

    def get_history(self, room_id: str) -> list[dict]:
        room = self.rooms.get(room_id)
        if room is None:
            return []
        return [asdict(msg) for msg in room.history]

    def get_room_ids(self) -> list[str]:
        return [rid for rid, room in self.rooms.items() if len(room.connections) > 0]

    @staticmethod
    def _timestamp() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())


# ── App ──

app = FastAPI(title="WebSocket Chat Server")
manager = RoomManager()


# ── REST Endpoints ──

class UserListResponse(BaseModel):
    room_id: str
    users: list[str]


class RoomListResponse(BaseModel):
    rooms: list[str]


@app.get("/rooms/{room_id}/users")
async def get_room_users(room_id: str) -> UserListResponse:
    users = manager.get_users(room_id)
    return UserListResponse(room_id=room_id, users=users)


@app.get("/rooms/{room_id}/history")
async def get_room_history(room_id: str) -> list[dict]:
    return manager.get_history(room_id)


@app.get("/rooms")
async def list_rooms() -> RoomListResponse:
    return RoomListResponse(rooms=manager.get_room_ids())


# ── WebSocket Endpoint ──

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, nickname: str = "anonymous") -> None:
    await websocket.accept()
    await manager.join(room_id, websocket, nickname)

    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast_message(room_id, websocket, data)
    except WebSocketDisconnect:
        await manager.leave(room_id, websocket)
    except Exception:
        await manager.leave(room_id, websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
