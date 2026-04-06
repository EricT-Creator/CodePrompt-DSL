from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, List, Set
import json
import asyncio
from datetime import datetime
from dataclasses import dataclass
import time

app = FastAPI()

@dataclass
class Room:
    connections: Set[WebSocket]
    nicknames: Dict[WebSocket, str]
    history: List[dict]

rooms: Dict[str, Room] = {}

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    nickname = websocket.query_params.get("nickname", "")
    if not nickname or not room_id:
        await websocket.close(code=1008, reason="Invalid parameters")
        return
    
    await websocket.accept()
    
    if room_id not in rooms:
        rooms[room_id] = Room(connections=set(), nicknames={}, history=[])
    
    room = rooms[room_id]
    room.connections.add(websocket)
    room.nicknames[websocket] = nickname
    
    join_message = {
        "sender": "System",
        "text": f"{nickname} joined the chat",
        "timestamp": datetime.now().isoformat(),
        "type": "join"
    }
    
    await broadcast_message(room, join_message)
    
    try:
        while True:
            message_text = await websocket.receive_text()
            user_message = {
                "sender": nickname,
                "text": message_text,
                "timestamp": datetime.now().isoformat(),
                "type": "message"
            }
            
            await broadcast_message(room, user_message)
            
    except WebSocketDisconnect:
        room.connections.remove(websocket)
        del room.nicknames[websocket]
        
        leave_message = {
            "sender": "System",
            "text": f"{nickname} left the chat",
            "timestamp": datetime.now().isoformat(),
            "type": "leave"
        }
        
        await broadcast_message(room, leave_message)
        
        if not room.connections:
            del rooms[room_id]

async def broadcast_message(room: Room, message: dict):
    room.history.append(message)
    if len(room.history) > 100:
        room.history = room.history[-100:]
    
    connections_list = list(room.connections)
    for connection in connections_list:
        try:
            await connection.send_text(json.dumps(message))
        except:
            if connection in room.connections:
                room.connections.remove(connection)
                if connection in room.nicknames:
                    del room.nicknames[connection]

@app.get("/rooms/{room_id}/history")
async def get_history(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    return rooms[room_id].history

@app.get("/rooms/{room_id}/users")
async def get_users(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = rooms[room_id]
    return list(room.nicknames.values())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)