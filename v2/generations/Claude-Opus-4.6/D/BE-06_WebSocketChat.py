from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import Dict, List, Set
import json
import time

app = FastAPI()


class ChatRoom:
    def __init__(self, name: str):
        self.name = name
        self.connections: Dict[WebSocket, str] = {}
        self.history: List[dict] = []
        self.max_history = 50

    @property
    def member_count(self) -> int:
        return len(self.connections)

    def add_message(self, message: dict):
        self.history.append(message)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

    async def broadcast(self, message: dict, exclude: WebSocket = None):
        self.add_message(message)
        payload = json.dumps(message)
        disconnected: List[WebSocket] = []
        for ws in self.connections:
            if ws == exclude:
                continue
            try:
                await ws.send_text(payload)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.connections.pop(ws, None)


class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, ChatRoom] = {}

    def get_or_create_room(self, room_name: str) -> ChatRoom:
        if room_name not in self.rooms:
            self.rooms[room_name] = ChatRoom(room_name)
        return self.rooms[room_name]

    def get_active_rooms(self) -> List[dict]:
        active = []
        for name, room in self.rooms.items():
            if room.member_count > 0:
                active.append({
                    "room": name,
                    "members": room.member_count,
                    "nicknames": list(room.connections.values()),
                })
        return active

    def cleanup_room(self, room_name: str):
        room = self.rooms.get(room_name)
        if room and room.member_count == 0:
            pass


manager = RoomManager()


@app.get("/rooms")
async def list_rooms():
    return JSONResponse(content={"rooms": manager.get_active_rooms()})


@app.websocket("/ws/{room_name}")
async def websocket_endpoint(websocket: WebSocket, room_name: str):
    await websocket.accept()
    room = manager.get_or_create_room(room_name)
    nickname = None

    try:
        first_message = await websocket.receive_text()
        nickname = first_message.strip() or f"User-{id(websocket) % 10000}"
        room.connections[websocket] = nickname

        await websocket.send_text(json.dumps({
            "type": "system",
            "content": f"Welcome to #{room_name}, {nickname}! ({room.member_count} online)",
            "timestamp": time.time(),
        }))

        if room.history:
            await websocket.send_text(json.dumps({
                "type": "history",
                "messages": room.history[-50:],
                "timestamp": time.time(),
            }))

        await room.broadcast(
            {
                "type": "system",
                "content": f"{nickname} joined the room",
                "timestamp": time.time(),
            },
            exclude=websocket,
        )

        while True:
            data = await websocket.receive_text()
            message = {
                "type": "message",
                "nickname": nickname,
                "content": data,
                "room": room_name,
                "timestamp": time.time(),
            }
            await room.broadcast(message)

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        room.connections.pop(websocket, None)
        if nickname:
            await room.broadcast(
                {
                    "type": "system",
                    "content": f"{nickname} left the room",
                    "timestamp": time.time(),
                }
            )
        manager.cleanup_room(room_name)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
