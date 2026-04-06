from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List, Set

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.histories: Dict[str, List[str]] = {}

    async def connect(self, room: str, websocket: WebSocket):
        await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = set()
            self.histories[room] = []
        self.active_connections[room].add(websocket)

    def disconnect(self, room: str, websocket: WebSocket):
        self.active_connections[room].remove(websocket)

    async def broadcast(self, room: str, message: str):
        self.histories[room].append(message)
        if len(self.histories[room]) > 50: self.histories[room].pop(0)
        for connection in self.active_connections[room]:
            await connection.send_text(message)

manager = ConnectionManager()

@app.get("/rooms")
def get_rooms():
    return {room: len(cons) for room, cons in manager.active_connections.items()}

@app.websocket("/ws/{room}/{nickname}")
async def websocket_endpoint(websocket: WebSocket, room: str, nickname: str):
    await manager.connect(room, websocket)
    await manager.broadcast(room, f"{nickname} joined")
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(room, f"{nickname}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(room, websocket)
        await manager.broadcast(room, f"{nickname} left")
