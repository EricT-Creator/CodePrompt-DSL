from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, List, Set
import json
from datetime import datetime
from dataclasses import dataclass, field

app = FastAPI()

@dataclass
class WebSocketChatRoom:
    active_connections: Set[WebSocket] = field(default_factory=set)
    user_mapping: Dict[WebSocket, str] = field(default_factory=dict)
    chat_log: List[dict] = field(default_factory=list)

chat_rooms_db: Dict[str, WebSocketChatRoom] = {}

@app.websocket("/ws/{room_id}")
async def handle_websocket_connection(websocket: WebSocket, room_id: str):
    user_name = websocket.query_params.get("nickname", "").strip()
    
    if not user_name or not room_id:
        await websocket.close(code=1008, reason="Invalid connection parameters")
        return
    
    await websocket.accept()
    
    if room_id not in chat_rooms_db:
        chat_rooms_db[room_id] = WebSocketChatRoom()
    
    current_room = chat_rooms_db[room_id]
    current_room.active_connections.add(websocket)
    current_room.user_mapping[websocket] = user_name
    
    system_announcement = {
        "event": "user_joined",
        "username": user_name,
        "timestamp": datetime.now().isoformat(),
        "online_count": len(current_room.active_connections)
    }
    
    await distribute_message(current_room, system_announcement)
    
    try:
        while True:
            message_content = await websocket.receive_text()
            
            chat_entry = {
                "event": "message",
                "username": user_name,
                "content": message_content,
                "timestamp": datetime.now().isoformat()
            }
            
            await distribute_message(current_room, chat_entry)
            
    except WebSocketDisconnect:
        if websocket in current_room.active_connections:
            current_room.active_connections.remove(websocket)
        
        if websocket in current_room.user_mapping:
            username = current_room.user_mapping[websocket]
            del current_room.user_mapping[websocket]
            
            departure_notice = {
                "event": "user_left",
                "username": username,
                "timestamp": datetime.now().isoformat(),
                "online_count": len(current_room.active_connections)
            }
            
            if current_room.active_connections:
                await distribute_message(current_room, departure_notice)
            
            if not current_room.active_connections:
                del chat_rooms_db[room_id]

async def distribute_message(room: WebSocketChatRoom, message: dict):
    room.chat_log.append(message)
    if len(room.chat_log) > 100:
        room.chat_log = room.chat_log[-100:]
    
    connections_copy = list(room.active_connections)
    for connection in connections_copy:
        try:
            await connection.send_text(json.dumps(message))
        except Exception:
            if connection in room.active_connections:
                room.active_connections.remove(connection)
            if connection in room.user_mapping:
                del room.user_mapping[connection]

@app.get("/rooms/{room_id}/history")
async def retrieve_chat_history(room_id: str):
    if room_id not in chat_rooms_db:
        raise HTTPException(status_code=404, detail="Chat room does not exist")
    
    return chat_rooms_db[room_id].chat_log

@app.get("/rooms/{room_id}/users")
async def get_active_users(room_id: str):
    if room_id not in chat_rooms_db:
        raise HTTPException(status_code=404, detail="Chat room does not exist")
    
    room = chat_rooms_db[room_id]
    return [{"nickname": name, "status": "online"} for name in room.user_mapping.values()]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)