from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import json
from typing import Dict, Set, List
from dataclasses import dataclass, field

app = FastAPI()

@dataclass
class Room:
    connections: Set[WebSocket] = field(default_factory=set)
    message_history: List[dict] = field(default_factory=list)
    nicknames: Dict[WebSocket, str] = field(default_factory=dict)

rooms: Dict[str, Room] = {}
MAX_HISTORY = 50

async def broadcast(room: Room, message: dict, exclude: WebSocket = None):
    for connection in room.connections:
        if connection != exclude:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                pass

@app.websocket("/ws/{room_name}")
async def websocket_endpoint(websocket: WebSocket, room_name: str):
    await websocket.accept()
    
    if room_name not in rooms:
        rooms[room_name] = Room()
    
    room = rooms[room_name]
    room.connections.add(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if "nickname" in message_data and websocket not in room.nicknames:
                nickname = message_data["nickname"]
                room.nicknames[websocket] = nickname
                join_message = {"type": "system", "content": f"{nickname} 加入了房间"}
                await broadcast(room, join_message)
                
                for msg in room.message_history:
                    await websocket.send_text(json.dumps(msg))
                continue
            
            if websocket not in room.nicknames:
                await websocket.send_text(json.dumps({"type": "error", "content": "请先设置昵称"}))
                continue
            
            nickname = room.nicknames[websocket]
            chat_message = {
                "type": "chat",
                "nickname": nickname,
                "content": message_data.get("content", ""),
            }
            
            room.message_history.append(chat_message)
            if len(room.message_history) > MAX_HISTORY:
                room.message_history.pop(0)
            
            await broadcast(room, chat_message)
            
    except WebSocketDisconnect:
        if room_name in rooms:
            room.connections.discard(websocket)
            if websocket in room.nicknames:
                nickname = room.nicknames.pop(websocket)
                leave_message = {"type": "system", "content": f"{nickname} 离开了房间"}
                await broadcast(room, leave_message)
            
            if len(room.connections) == 0:
                del rooms[room_name]

@app.get("/rooms")
def get_rooms():
    room_list = []
    for name, room in rooms.items():
        room_list.append({
            "name": name,
            "user_count": len(room.connections)
        })
    return {"rooms": room_list}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
