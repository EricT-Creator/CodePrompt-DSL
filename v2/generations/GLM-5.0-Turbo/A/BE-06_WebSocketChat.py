import asyncio
import time
from typing import Dict, Set, List
from collections import defaultdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

# Room management
class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, Dict[str, WebSocket]] = defaultdict(dict)
        self.message_history: Dict[str, List[dict]] = defaultdict(list)
        self.max_history = 50

    def join_room(self, room_name: str, nickname: str, websocket: WebSocket):
        self.rooms[room_name][nickname] = websocket
        if len(self.message_history[room_name]) > 0:
            return self.message_history[room_name][-self.max_history:]

    def leave_room(self, room_name: str, nickname: str):
        if room_name in self.rooms and nickname in self.rooms[room_name]:
            del self.rooms[room_name][nickname]
        if room_name in self.rooms and len(self.rooms[room_name]) == 0:
            del self.rooms[room_name]

    def add_message(self, room_name: str, nickname: str, content: str) -> dict:
        msg = {
            "nickname": nickname,
            "content": content,
            "timestamp": time.strftime("%H:%M:%S"),
        }
        history = self.message_history[room_name]
        history.append(msg)
        if len(history) > self.max_history:
            self.message_history[room_name] = history[-self.max_history:]
        return msg

    async def broadcast(self, room_name: str, message: dict, exclude: str | None = None):
        if room_name not in self.rooms:
            return
        disconnected = []
        for nickname, ws in self.rooms[room_name].items():
            if exclude and nickname == exclude:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(nickname)
        for nick in disconnected:
            self.leave_room(room_name, nick)

    def get_active_rooms(self) -> List[dict]:
        result = []
        for room_name, members in self.rooms.items():
            result.append({
                "name": room_name,
                "users": len(members),
                "nicknames": list(members.keys()),
            })
        return result


manager = RoomManager()


@app.get("/rooms")
async def list_rooms():
    rooms = manager.get_active_rooms()
    return {"rooms": rooms, "total": len(rooms)}


@app.websocket("/ws/{room_name}")
async def websocket_chat(websocket: WebSocket, room_name: str):
    await websocket.accept()
    nickname = None
    try:
        # First message must be the nickname
        data = await websocket.receive_text()
        nickname = data.strip()
        if not nickname:
            await websocket.close(code=4001, reason="Nickname required")
            return

        history = manager.join_room(room_name, nickname, websocket)
        if history:
            await websocket.send_json({"type": "history", "messages": history})

        join_msg = {"type": "system", "content": f"{nickname} joined the room"}
        await manager.broadcast(room_name, join_msg)

        while True:
            data = await websocket.receive_text()
            if not data.strip():
                continue
            msg = manager.add_message(room_name, nickname, data.strip())
            await manager.broadcast(room_name, {"type": "message", **msg})

    except WebSocketDisconnect:
        pass
    finally:
        if nickname:
            manager.leave_room(room_name, nickname)
            leave_msg = {"type": "system", "content": f"{nickname} left the room"}
            await manager.broadcast(room_name, leave_msg)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
