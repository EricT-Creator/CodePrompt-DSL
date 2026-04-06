import asyncio
import time
import json
from typing import Dict, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse

app = FastAPI()

# Room storage
class Room:
    def __init__(self, name: str):
        self.name: str = name
        self.connections: Dict[str, WebSocket] = {}
        self.history: list = []  # last 50 messages
        self.created_at: float = time.time()

    def add_user(self, nickname: str, ws: WebSocket):
        self.connections[nickname] = ws

    def remove_user(self, nickname: str):
        self.connections.pop(nickname, None)

    def add_message(self, nickname: str, text: str) -> dict:
        msg = {
            "nickname": nickname,
            "text": text,
            "timestamp": time.time(),
            "type": "message",
        }
        self.history.append(msg)
        if len(self.history) > 50:
            self.history = self.history[-50:]
        return msg

    def user_count(self) -> int:
        return len(self.connections)

    def to_summary(self) -> dict:
        return {
            "name": self.name,
            "users": list(self.connections.keys()),
            "user_count": len(self.connections),
        }


rooms: Dict[str, Room] = {
    "general": Room("general"),
    "random": Room("random"),
    "tech": Room("tech"),
}


@app.get("/rooms")
async def list_rooms():
    return {
        "rooms": [room.to_summary() for room in rooms.values()],
        "total": len(rooms),
    }


@app.websocket("/ws/chat/{room_name}")
async def websocket_chat(websocket: WebSocket, room_name: str):
    # Validate room exists, create if not
    if room_name not in rooms:
        rooms[room_name] = Room(room_name)

    room = rooms[room_name]

    await websocket.accept()

    # Wait for nickname registration
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=15)
        data = json.loads(raw)
        if data.get("type") != "join" or not data.get("nickname"):
            await websocket.send_text(json.dumps({
                "type": "error",
                "text": "First message must be a join with nickname",
            }))
            await websocket.close()
            return

        nickname = data["nickname"].strip()
        if not nickname:
            await websocket.send_text(json.dumps({
                "type": "error",
                "text": "Nickname cannot be empty",
            }))
            await websocket.close()
            return

        # Check if nickname already in room
        if nickname in room.connections:
            await websocket.send_text(json.dumps({
                "type": "error",
                "text": f"Nickname '{nickname}' is already taken in this room",
            }))
            await websocket.close()
            return

        room.add_user(nickname, websocket)

        # Send history
        await websocket.send_text(json.dumps({
            "type": "history",
            "messages": room.history,
        }))

        # Broadcast join notification
        join_msg = {
            "type": "system",
            "text": f"{nickname} joined the room",
            "timestamp": time.time(),
        }
        for name, conn in room.connections.items():
            if name != nickname:
                try:
                    await conn.send_text(json.dumps(join_msg))
                except Exception:
                    pass

        # Send updated user list
        await broadcast_user_list(room)

    except asyncio.TimeoutError:
        await websocket.close()
        return
    except Exception:
        return

    # Main message loop
    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            text = data.get("text", "").strip()
            if not text:
                continue

            msg = room.add_message(nickname, text)

            # Broadcast via set iteration
            disconnected = []
            for name, conn in room.connections.items():
                try:
                    await conn.send_text(json.dumps(msg))
                except Exception:
                    disconnected.append(name)

            for name in disconnected:
                room.remove_user(name)

    except WebSocketDisconnect:
        pass
    finally:
        room.remove_user(nickname)
        if room.user_count() == 0 and room.name not in ("general", "random", "tech"):
            rooms.pop(room.name, None)

        leave_msg = {
            "type": "system",
            "text": f"{nickname} left the room",
            "timestamp": time.time(),
        }
        for name, conn in room.connections.items():
            try:
                await conn.send_text(json.dumps(leave_msg))
            except Exception:
                pass

        await broadcast_user_list(room)


async def broadcast_user_list(room: Room):
    user_list_msg = {
        "type": "user_list",
        "users": list(room.connections.keys()),
        "user_count": room.user_count(),
    }
    disconnected = []
    for name, conn in room.connections.items():
        try:
            await conn.send_text(json.dumps(user_list_msg))
        except Exception:
            disconnected.append(name)
    for name in disconnected:
        room.remove_user(name)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
