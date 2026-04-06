import time
from typing import Dict, List, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

app = FastAPI()


class ChatRoom:
    def __init__(self, name: str):
        self.name = name
        self.connections: Dict[WebSocket, str] = {}
        self.history: List[dict] = []
        self.max_history = 50

    def add_message(self, nickname: str, content: str):
        msg = {
            "nickname": nickname,
            "content": content,
            "timestamp": time.time(),
            "room": self.name,
        }
        self.history.append(msg)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        return msg

    async def broadcast(self, message: dict, exclude: WebSocket = None):
        import json
        payload = json.dumps(message)
        disconnected: List[WebSocket] = []
        for ws in self.connections:
            if ws is exclude:
                continue
            try:
                await ws.send_text(payload)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.connections.pop(ws, None)


rooms: Dict[str, ChatRoom] = {}


def get_or_create_room(room_name: str) -> ChatRoom:
    if room_name not in rooms:
        rooms[room_name] = ChatRoom(room_name)
    return rooms[room_name]


def cleanup_empty_rooms():
    empty = [name for name, room in rooms.items() if len(room.connections) == 0]
    for name in empty:
        del rooms[name]


@app.websocket("/ws/{room_name}")
async def websocket_endpoint(websocket: WebSocket, room_name: str):
    await websocket.accept()
    room = get_or_create_room(room_name)
    nickname: str = ""

    try:
        first_msg = await websocket.receive_text()
        nickname = first_msg.strip() or f"anon-{id(websocket) % 10000}"
        room.connections[websocket] = nickname

        import json
        if room.history:
            await websocket.send_text(json.dumps({
                "type": "history",
                "messages": room.history,
            }))

        join_msg = room.add_message("system", f"{nickname} joined the room")
        await room.broadcast({"type": "message", **join_msg}, exclude=websocket)
        await websocket.send_text(json.dumps({
            "type": "system",
            "content": f"Welcome to #{room_name}, {nickname}! ({len(room.connections)} online)",
        }))

        while True:
            data = await websocket.receive_text()
            msg = room.add_message(nickname, data)
            await room.broadcast({"type": "message", **msg})

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        room.connections.pop(websocket, None)
        if nickname:
            leave_msg = room.add_message("system", f"{nickname} left the room")
            import json
            await room.broadcast({"type": "message", **leave_msg})
        cleanup_empty_rooms()


@app.get("/rooms")
async def list_rooms():
    result = []
    for name, room in rooms.items():
        result.append({
            "room": name,
            "online_count": len(room.connections),
            "nicknames": list(room.connections.values()),
        })
    return {"active_rooms": result, "total": len(result)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
