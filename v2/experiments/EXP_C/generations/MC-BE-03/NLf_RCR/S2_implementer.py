import json
import uuid
from datetime import datetime
from typing import Dict, List, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

app = FastAPI()

rooms: Dict[str, Set[WebSocket]] = {}
user_info: Dict[WebSocket, dict] = {}
message_history: Dict[str, List[dict]] = {}
MAX_HISTORY = 100

class Message(BaseModel):
    id: str
    room_id: str
    nickname: str
    content: str
    timestamp: str
    type: str

class RoomInfo(BaseModel):
    room_id: str
    online_count: int
    users: List[str]

async def broadcast(room_id: str, message: dict):
    if room_id not in rooms:
        return
    stale = set()
    for ws in rooms[room_id]:
        try:
            await ws.send_json(message)
        except Exception:
            stale.add(ws)
    for ws in stale:
        rooms[room_id].discard(ws)
        user_info.pop(ws, None)
    if not rooms[room_id]:
        del rooms[room_id]

def store_message(room_id: str, message: dict):
    if room_id not in message_history:
        message_history[room_id] = []
    message_history[room_id].append(message)
    if len(message_history[room_id]) > MAX_HISTORY:
        message_history[room_id].pop(0)

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, nickname: str = "Anonymous"):
    await websocket.accept()
    
    if room_id not in rooms:
        rooms[room_id] = set()
    rooms[room_id].add(websocket)
    user_info[websocket] = {"nickname": nickname, "room_id": room_id, "connected_at": datetime.utcnow().isoformat()}
    
    join_message = {
        "id": str(uuid.uuid4()),
        "room_id": room_id,
        "nickname": "system",
        "content": f"{nickname} joined the room",
        "timestamp": datetime.utcnow().isoformat(),
        "type": "system"
    }
    store_message(room_id, join_message)
    await broadcast(room_id, join_message)
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                parsed = json.loads(data)
                content = parsed.get("content", "")
                if content:
                    message = {
                        "id": str(uuid.uuid4()),
                        "room_id": room_id,
                        "nickname": nickname,
                        "content": content,
                        "timestamp": datetime.utcnow().isoformat(),
                        "type": "user"
                    }
                    store_message(room_id, message)
                    await broadcast(room_id, message)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
    except WebSocketDisconnect:
        rooms[room_id].discard(websocket)
        user_info.pop(websocket, None)
        if not rooms[room_id]:
            del rooms[room_id]
        
        leave_message = {
            "id": str(uuid.uuid4()),
            "room_id": room_id,
            "nickname": "system",
            "content": f"{nickname} left the room",
            "timestamp": datetime.utcnow().isoformat(),
            "type": "system"
        }
        if room_id in rooms:
            store_message(room_id, leave_message)
            await broadcast(room_id, leave_message)

@app.get("/rooms")
async def list_rooms():
    result = []
    for room_id in rooms:
        users = [user_info[ws]["nickname"] for ws in rooms[room_id] if ws in user_info]
        result.append({"room_id": room_id, "online_count": len(rooms[room_id]), "users": users})
    return result

@app.get("/rooms/{room_id}/users")
async def get_room_users(room_id: str):
    if room_id not in rooms:
        return {"room_id": room_id, "online_count": 0, "users": []}
    users = [user_info[ws]["nickname"] for ws in rooms[room_id] if ws in user_info]
    return {"room_id": room_id, "online_count": len(users), "users": users}

@app.get("/rooms/{room_id}/history")
async def get_room_history(room_id: str):
    return message_history.get(room_id, [])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
