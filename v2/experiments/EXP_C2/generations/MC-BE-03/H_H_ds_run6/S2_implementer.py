from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, List, Set
import json
from datetime import datetime
from dataclasses import dataclass

app = FastAPI()

@dataclass
class ChatRoom:
    connections: Set[WebSocket]
    nicknames: Dict[WebSocket, str]
    message_history: List[dict]

chat_rooms: Dict[str, ChatRoom] = {}

@app.websocket("/ws/{room_id}")
async def websocket_chat(websocket: WebSocket, room_id: str):
    nickname = websocket.query_params.get("nickname", "")
    
    if not nickname.strip() or not room_id.strip():
        await websocket.close(code=1008)
        return
    
    await websocket.accept()
    
    if room_id not in chat_rooms:
        chat_rooms[room_id] = ChatRoom(
            connections=set(),
            nicknames={},
            message_history=[]
        )
    
    room = chat_rooms[room_id]
    room.connections.add(websocket)
    room.nicknames[websocket] = nickname
    
    join_notification = {
        "type": "system",
        "content": f"User '{nickname}' has joined the room",
        "timestamp": datetime.now().isoformat(),
        "user_count": len(room.connections)
    }
    
    await send_to_all(room, join_notification)
    
    try:
        while True:
            data = await websocket.receive_text()
            user_msg = {
                "type": "user",
                "sender": nickname,
                "content": data,
                "timestamp": datetime.now().isoformat()
            }
            
            await send_to_all(room, user_msg)
            
    except WebSocketDisconnect:
        if websocket in room.connections:
            room.connections.remove(websocket)
        
        if websocket in room.nicknames:
            del room.nicknames[websocket]
        
        leave_notification = {
            "type": "system",
            "content": f"User '{nickname}' has left the room",
            "timestamp": datetime.now().isoformat(),
            "user_count": len(room.connections)
        }
        
        if room.connections:
            await send_to_all(room, leave_notification)
        
        if not room.connections:
            del chat_rooms[room_id]

async def send_to_all(room: ChatRoom, message: dict):
    room.message_history.append(message)
    if len(room.message_history) > 100:
        room.message_history = room.message_history[-100:]
    
    for ws in list(room.connections):
        try:
            await ws.send_text(json.dumps(message))
        except:
            if ws in room.connections:
                room.connections.remove(ws)
            if ws in room.nicknames:
                del room.nicknames[ws]

@app.get("/rooms/{room_id}/history")
async def chat_history(room_id: str):
    if room_id not in chat_rooms:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    return chat_rooms[room_id].message_history

@app.get("/rooms/{room_id}/users")
async def online_users(room_id: str):
    if room_id not in chat_rooms:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    room = chat_rooms[room_id]
    return [{"nickname": name, "online": True} for name in room.nicknames.values()]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)