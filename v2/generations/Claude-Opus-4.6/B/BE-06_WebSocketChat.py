import time
from typing import Dict, List, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

app = FastAPI(title="WebSocket Chat Server")

MAX_HISTORY = 50


class ChatRoom:
    def __init__(self, name: str):
        self.name = name
        self.connections: Dict[WebSocket, str] = {}
        self.history: List[dict] = []

    @property
    def user_count(self) -> int:
        return len(self.connections)

    def add_message(self, message: dict) -> None:
        self.history.append(message)
        if len(self.history) > MAX_HISTORY:
            self.history = self.history[-MAX_HISTORY:]

    async def broadcast(self, message: dict, exclude: WebSocket = None) -> None:
        self.add_message(message)
        disconnected: Set[WebSocket] = set()
        for ws in self.connections:
            if ws is exclude:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.add(ws)
        for ws in disconnected:
            self.remove_connection(ws)

    def add_connection(self, ws: WebSocket, nickname: str) -> None:
        self.connections[ws] = nickname

    def remove_connection(self, ws: WebSocket) -> str:
        return self.connections.pop(ws, "unknown")

    def get_nicknames(self) -> List[str]:
        return list(self.connections.values())


rooms: Dict[str, ChatRoom] = {}


def get_or_create_room(room_name: str) -> ChatRoom:
    if room_name not in rooms:
        rooms[room_name] = ChatRoom(room_name)
    return rooms[room_name]


@app.get("/rooms")
async def list_rooms():
    result = {}
    for name, room in rooms.items():
        result[name] = {
            "user_count": room.user_count,
            "users": room.get_nicknames(),
        }
    return result


@app.websocket("/ws/{room_name}")
async def websocket_endpoint(websocket: WebSocket, room_name: str, nickname: str = "anonymous"):
    await websocket.accept()
    room = get_or_create_room(room_name)
    room.add_connection(websocket, nickname)

    # Send history to the new user
    try:
        await websocket.send_json({
            "type": "history",
            "room": room_name,
            "messages": room.history,
        })
    except Exception:
        pass

    # Broadcast join notification
    join_msg = {
        "type": "system",
        "room": room_name,
        "content": f"{nickname} joined the room",
        "timestamp": time.time(),
    }
    await room.broadcast(join_msg)

    try:
        while True:
            data = await websocket.receive_json()
            content = data.get("content", "")
            if not content:
                continue
            msg = {
                "type": "message",
                "room": room_name,
                "nickname": nickname,
                "content": content,
                "timestamp": time.time(),
            }
            await room.broadcast(msg)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        removed_nick = room.remove_connection(websocket)
        leave_msg = {
            "type": "system",
            "room": room_name,
            "content": f"{removed_nick} left the room",
            "timestamp": time.time(),
        }
        await room.broadcast(leave_msg)

        # Cleanup empty rooms
        if room.user_count == 0:
            rooms.pop(room_name, None)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
