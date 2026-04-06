import json
import time
from collections import deque
from dataclasses import dataclass, asdict
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse


# ---- Data Models ----

@dataclass
class ChatMessage:
    nickname: str
    content: str
    timestamp: str
    msg_type: str  # "user" | "system"


# ---- Room Management ----

class Room:
    def __init__(self) -> None:
        self.connections: dict[WebSocket, str] = {}
        self.history: deque[ChatMessage] = deque(maxlen=100)


class RoomManager:
    def __init__(self) -> None:
        self.rooms: dict[str, Room] = {}

    def get_or_create_room(self, room_id: str) -> Room:
        if room_id not in self.rooms:
            self.rooms[room_id] = Room()
        return self.rooms[room_id]

    def join(self, room_id: str, ws: WebSocket, nickname: str) -> Room:
        room = self.get_or_create_room(room_id)
        room.connections[ws] = nickname
        return room

    def leave(self, room_id: str, ws: WebSocket) -> str | None:
        room = self.rooms.get(room_id)
        if room is None:
            return None
        nickname = room.connections.pop(ws, None)
        return nickname

    def get_users(self, room_id: str) -> list[str]:
        room = self.rooms.get(room_id)
        if room is None:
            return []
        return list(room.connections.values())

    def get_history(self, room_id: str) -> list[dict[str, Any]]:
        room = self.rooms.get(room_id)
        if room is None:
            return []
        return [asdict(msg) for msg in room.history]

    def get_active_rooms(self) -> list[str]:
        return [rid for rid, room in self.rooms.items() if len(room.connections) > 0]

    async def broadcast(self, room_id: str, message: ChatMessage, exclude: WebSocket | None = None) -> None:
        room = self.rooms.get(room_id)
        if room is None:
            return

        room.history.append(message)
        msg_json = json.dumps(asdict(message))

        disconnected: list[WebSocket] = []
        for ws in list(room.connections.keys()):
            if ws is exclude:
                continue
            try:
                await ws.send_text(msg_json)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            room.connections.pop(ws, None)


# ---- App ----

app = FastAPI(title="WebSocket Chat Server")
manager = RoomManager()


def make_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())


# ---- WebSocket Endpoint ----

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, nickname: str = Query(...)) -> None:
    await websocket.accept()
    room = manager.join(room_id, websocket, nickname)

    # Send history to the new client
    history = [asdict(msg) for msg in room.history]
    await websocket.send_text(json.dumps({"type": "history", "messages": history}))

    # Broadcast join
    join_msg = ChatMessage(
        nickname=nickname,
        content=f"{nickname} has joined the room.",
        timestamp=make_timestamp(),
        msg_type="system",
    )
    await manager.broadcast(room_id, join_msg, exclude=None)

    try:
        while True:
            data = await websocket.receive_text()
            chat_msg = ChatMessage(
                nickname=nickname,
                content=data,
                timestamp=make_timestamp(),
                msg_type="user",
            )
            await manager.broadcast(room_id, chat_msg, exclude=websocket)
            # Also send back to sender for confirmation
            await websocket.send_text(json.dumps(asdict(chat_msg)))
    except WebSocketDisconnect:
        left_nickname = manager.leave(room_id, websocket)
        if left_nickname:
            leave_msg = ChatMessage(
                nickname=left_nickname,
                content=f"{left_nickname} has left the room.",
                timestamp=make_timestamp(),
                msg_type="system",
            )
            await manager.broadcast(room_id, leave_msg, exclude=None)


# ---- REST Endpoints ----

@app.get("/rooms")
async def list_rooms() -> list[str]:
    return manager.get_active_rooms()


@app.get("/rooms/{room_id}/users")
async def get_room_users(room_id: str) -> list[str]:
    return manager.get_users(room_id)


@app.get("/rooms/{room_id}/history")
async def get_room_history(room_id: str) -> list[dict[str, Any]]:
    return manager.get_history(room_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
