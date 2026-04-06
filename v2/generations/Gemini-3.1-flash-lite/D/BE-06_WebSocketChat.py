from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from collections import deque

app = FastAPI()

rooms = {}

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()
    if room_id not in rooms:
        rooms[room_id] = {"connections": set(), "history": deque(maxlen=50)}
    
    rooms[room_id]["connections"].add(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            rooms[room_id]["history"].append(data)
            for connection in rooms[room_id]["connections"]:
                await connection.send_text(data)
    except WebSocketDisconnect:
        rooms[room_id]["connections"].remove(websocket)

@app.get("/rooms")
def get_rooms():
    return {room: len(data["connections"]) for room, data in rooms.items()}
