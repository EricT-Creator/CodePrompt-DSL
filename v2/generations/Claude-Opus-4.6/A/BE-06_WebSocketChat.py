from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

app = FastAPI()


@dataclass
class Message:
    nickname: str
    content: str
    timestamp: float


@dataclass
class Room:
    name: str
    connections: Dict[WebSocket, str] = field(default_factory=dict)
    history: List[Message] = field(default_factory=list)
    max_history: int = 50

    @property
    def user_count(self) -> int:
        return len(self.connections)

    def add_message(self, nickname: str, content: str) -> Message:
        msg = Message(nickname=nickname, content=content, timestamp=time.time())
        self.history.append(msg)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        return msg


class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, Room] = {}

    def get_or_create_room(self, room_name: str) -> Room:
        if room_name not in self.rooms:
            self.rooms[room_name] = Room(name=room_name)
        return self.rooms[room_name]

    def get_active_rooms(self) -> List[dict]:
        result = []
        for name, room in self.rooms.items():
            if room.user_count > 0:
                result.append({
                    "room": name,
                    "users": room.user_count,
                    "nicknames": list(room.connections.values()),
                })
        return result

    async def connect(self, room_name: str, websocket: WebSocket, nickname: str) -> Room:
        room = self.get_or_create_room(room_name)
        room.connections[websocket] = nickname
        return room

    def disconnect(self, room_name: str, websocket: WebSocket) -> None:
        if room_name in self.rooms:
            room = self.rooms[room_name]
            nickname = room.connections.pop(websocket, None)
            if room.user_count == 0:
                del self.rooms[room_name]
            return nickname
        return None

    async def broadcast(self, room: Room, message: dict, exclude: WebSocket | None = None) -> None:
        disconnected = []
        for ws in room.connections:
            if ws is exclude:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            room.connections.pop(ws, None)


manager = RoomManager()


@app.get("/rooms")
async def list_rooms():
    rooms = manager.get_active_rooms()
    return {"rooms": rooms, "total_rooms": len(rooms)}


@app.websocket("/ws/{room_name}")
async def websocket_endpoint(websocket: WebSocket, room_name: str):
    await websocket.accept()

    try:
        first_message = await websocket.receive_text()
        nickname = first_message.strip() or "Anonymous"
    except WebSocketDisconnect:
        return

    room = await manager.connect(room_name, websocket, nickname)

    if room.history:
        history_messages = [
            {
                "type": "history",
                "nickname": msg.nickname,
                "content": msg.content,
                "timestamp": msg.timestamp,
            }
            for msg in room.history
        ]
        await websocket.send_json({"type": "history_batch", "messages": history_messages})

    await manager.broadcast(
        room,
        {
            "type": "system",
            "content": f"{nickname} joined the room",
            "timestamp": time.time(),
        },
        exclude=websocket,
    )

    try:
        while True:
            data = await websocket.receive_text()
            msg = room.add_message(nickname, data)
            await manager.broadcast(
                room,
                {
                    "type": "message",
                    "nickname": nickname,
                    "content": data,
                    "timestamp": msg.timestamp,
                },
            )
    except WebSocketDisconnect:
        left_nickname = manager.disconnect(room_name, websocket)
        if room_name in manager.rooms:
            await manager.broadcast(
                manager.rooms[room_name],
                {
                    "type": "system",
                    "content": f"{left_nickname or nickname} left the room",
                    "timestamp": time.time(),
                },
            )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
