from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, Set

app = FastAPI()

rooms: Dict[str, Set[WebSocket]] = {}
history: Dict[str, list] = {}

@app.websocket("/ws/{room}/{nickname}")
async def websocket_endpoint(websocket: WebSocket, room: str, nickname: str):
    await websocket.accept()
    if room not in rooms:
        rooms[room] = set()
        history[room] = []
    
    rooms[room].add(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = f"{nickname}: {data}"
            history[room].append(msg)
            if len(history[room]) > 50:
                history[room].pop(0)
            
            for client in rooms[room]:
                await client.send_text(msg)
    except WebSocketDisconnect:
        rooms[room].remove(websocket)

@app.get("/rooms")
async def get_rooms():
    return {room: len(clients) for room, clients in rooms.items()}
