from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, List, Set
import json
from datetime import datetime
from dataclasses import dataclass

app = FastAPI()

@dataclass
class ChatRoom:
    websockets: Set[WebSocket]
    usernames: Dict[WebSocket, str]
    messages: List[dict]

rooms: Dict[str, ChatRoom] = {}

@app.websocket("/ws/{room_id}")
async def chat_websocket(websocket: WebSocket, room_id: str):
    nickname = websocket.query_params.get("nickname", "")
    
    if not nickname or not room_id:
        await websocket.close(code=1008)
        return
    
    await websocket.accept()
    
    if room_id not in rooms:
        rooms[room_id] = ChatRoom(websockets=set(), usernames={}, messages=[])
    
    room = rooms[room_id]
    room.websockets.add(websocket)
    room.usernames[websocket] = nickname
    
    join_msg = {
        "type": "notification",
        "message": f"{nickname} has joined room {room_id}",
        "user": "system",
        "time": datetime.now().isoformat(),
        "active_users": len(room.websockets)
    }
    
    await send_to_room(room, join_msg)
    
    try:
        while True:
            text = await websocket.receive_text()
            
            chat_msg = {
                "type": "chat",
                "user": nickname,
                "message": text,
                "time": datetime.now().isoformat(),
                "room": room_id
            }
            
            await send_to_room(room, chat_msg)
            
    except WebSocketDisconnect:
        if websocket in room.websockets:
            room.websockets.remove(websocket)
        
        if websocket in room.usernames:
            left_user = room.usernames[websocket]
            del room.usernames[websocket]
            
            leave_msg = {
                "type": "notification",
                "message": f"{left_user} has left room {room_id}",
                "user": "system",
                "time": datetime.now().isoformat(),
                "active_users": len(room.websockets)
            }
            
            if room.websockets:
                await send_to_room(room, leave_msg)
        
        if not room.websockets:
            del rooms[room_id]

async def send_to_room(room: ChatRoom, message: dict):
    room.messages.append(message)
    if len(room.messages) > 100:
        room.messages = room.messages[-100:]
    
    for ws in list(room.websockets):
        try:
            await ws.send_text(json.dumps(message))
        except:
            if ws in room.websockets:
                room.websockets.remove(ws)
            if ws in room.usernames:
                del room.usernames[ws]

@app.get("/rooms/{room_id}/history")
async def room_history(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    return rooms[room_id].messages

@app.get("/rooms/{room_id}/users")
async def room_users(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = rooms[room_id]
    return [name for name in room.usernames.values()]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8080)