from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, List[WebSocket]] = {}
        self.history: Dict[str, List[str]] = {}

    async def connect(self, room: str, websocket: WebSocket):
        await websocket.accept()
        if room not in self.rooms: self.rooms[room] = []
        self.rooms[room].append(websocket)
        if room not in self.history: self.history[room] = []

    def disconnect(self, room: str, websocket: WebSocket):
        self.rooms[room].remove(websocket)

    async def broadcast(self, room: str, message: str):
        self.history[room].append(message)
        if len(self.history[room]) > 50: self.history[room].pop(0)
        for connection in self.rooms.get(room, []):
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str):
    await manager.connect(room, websocket)
    try:
        nickname = await websocket.receive_text()
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(room, f"{nickname}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(room, websocket)

@app.get("/rooms")
def get_rooms():
    return {room: len(conns) for room, conns in manager.rooms.items()}
