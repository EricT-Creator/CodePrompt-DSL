import json
import asyncio
import time
from collections import defaultdict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Set, List, Optional

app = FastAPI(title="WebSocket Chat (Multi-Room)")


class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, Set[WebSocket]] = defaultdict(set)
        self.nicknames: Dict[WebSocket, str] = {}
        self.histories: Dict[str, List[dict]] = defaultdict(list)
        self.max_history = 50

    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        self.rooms[room].add(websocket)

    def disconnect(self, websocket: WebSocket):
        nickname = self.nicknames.pop(websocket, None)
        for room_sockets in self.rooms.values():
            if websocket in room_sockets:
                room_sockets.discard(websocket)
                if nickname:
                    self.histories[next(k for k, v in self.rooms.items() if websocket in v)].append(
                        {"type": "system", "text": f"{nickname} left the room", "ts": time.time()}
                    )

    async def register(self, websocket: WebSocket, room: str, nickname: str):
        self.nicknames[websocket] = nickname
        self.rooms[room].add(websocket)
        self.histories[room].append(
            {"type": "system", "text": f"{nickname} joined the room", "ts": time.time()}
        )
        history = self.histories[room][-self.max_history:]
        await websocket.send_json({"type": "history", "messages": history})
        await self.broadcast_room(room, {"type": "system", "text": f"{nickname} joined the room", "ts": time.time()}, exclude=websocket)

    async def broadcast_room(self, room: str, message: dict, exclude: Optional[WebSocket] = None):
        disconnected = []
        for ws in self.rooms.get(room, set()):
            if ws == exclude:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)

    def get_room_info(self, room: str) -> dict:
        count = len(self.rooms.get(room, set()))
        return {"room": room, "active_users": count}

    def get_active_rooms(self) -> List[dict]:
        return [{"room": room, "active_users": len(sockets)} for room, sockets in self.rooms.items() if sockets]

    async def send_room_history(self, websocket: WebSocket, room: str):
        history = self.histories.get(room, [])[-self.max_history:]
        await websocket.send_json({"type": "history", "messages": history})


manager = ConnectionManager()


@app.websocket("/ws/chat/{room}")
async def websocket_chat(websocket: WebSocket, room: str):
    await manager.connect(websocket, room)
    try:
        registered = False
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "text": "Invalid JSON"})
                continue

            if not registered:
                nickname = msg.get("nickname", "").strip()
                if not nickname:
                    await websocket.send_json({"type": "error", "text": "Nickname required as first message"})
                    continue
                await manager.register(websocket, room, nickname)
                registered = True
                continue

            if msg.get("type") == "message":
                text = msg.get("text", "").strip()
                if not text:
                    continue
                nickname = manager.nicknames.get(websocket, "Anonymous")
                chat_msg = {
                    "type": "message",
                    "nickname": nickname,
                    "text": text,
                    "ts": time.time(),
                }
                manager.histories[room].append(chat_msg)
                if len(manager.histories[room]) > manager.max_history:
                    manager.histories[room] = manager.histories[room][-manager.max_history:]
                await manager.broadcast_room(room, chat_msg, exclude=websocket)
                await websocket.send_json({**chat_msg, "self": True})

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/rooms")
def get_rooms():
    return {"rooms": manager.get_active_rooms()}


@app.get("/rooms/{room}/history")
def get_room_history(room: str):
    history = manager.histories.get(room, [])
    return {"room": room, "history": history[-manager.max_history:], "count": len(history)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
