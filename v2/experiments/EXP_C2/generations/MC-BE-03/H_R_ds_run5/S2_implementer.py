from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Set, List
import asyncio
import json
from datetime import datetime
import logging

app = FastAPI(title="WebSocket Chat Server")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatRoom:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.connections: Set[WebSocket] = set()
        self.nicknames: Dict[WebSocket, str] = {}
        self.history: List[Dict] = []

    def add_user(self, websocket: WebSocket, nickname: str):
        self.connections.add(websocket)
        self.nicknames[websocket] = nickname

    def remove_user(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.remove(websocket)
        if websocket in self.nicknames:
            del self.nicknames[websocket]

    async def broadcast(self, sender_nickname: str, message: str):
        timestamp = datetime.utcnow().isoformat() + "Z"
        payload = {
            "sender": sender_nickname,
            "text": message,
            "timestamp": timestamp
        }
        
        failed_connections = []
        for conn in list(self.connections):
            try:
                await conn.send_text(json.dumps(payload))
            except Exception as e:
                logger.warning(f"Failed to send to {self.nicknames.get(conn, 'unknown')}: {e}")
                failed_connections.append(conn)
        
        for conn in failed_connections:
            self.remove_user(conn)
        
        self.history.append(payload)
        if len(self.history) > 100:
            self.history = self.history[-100:]

    async def broadcast_system(self, message: str):
        timestamp = datetime.utcnow().isoformat() + "Z"
        payload = {
            "sender": "system",
            "text": message,
            "timestamp": timestamp
        }
        
        failed_connections = []
        for conn in list(self.connections):
            try:
                await conn.send_text(json.dumps(payload))
            except Exception as e:
                logger.warning(f"Failed to send system message: {e}")
                failed_connections.append(conn)
        
        for conn in failed_connections:
            self.remove_user(conn)

rooms: Dict[str, ChatRoom] = {}

def get_or_create_room(room_id: str) -> ChatRoom:
    if room_id not in rooms:
        rooms[room_id] = ChatRoom(room_id)
        logger.info(f"Created new room: {room_id}")
    return rooms[room_id]

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    nickname = websocket.query_params.get("nickname", "").strip()
    
    if not nickname:
        await websocket.close(code=1008, reason="Nickname is required")
        return
    
    if not room_id or len(room_id) < 1:
        await websocket.close(code=1008, reason="Room ID is required")
        return
    
    await websocket.accept()
    
    room = get_or_create_room(room_id)
    room.add_user(websocket, nickname)
    
    try:
        await room.broadcast_system(f"{nickname} joined the chat")
        
        while True:
            message = await websocket.receive_text()
            if not message.strip():
                continue
            
            await room.broadcast(nickname, message.strip())
    
    except WebSocketDisconnect:
        logger.info(f"User {nickname} disconnected from room {room_id}")
        room.remove_user(websocket)
        await room.broadcast_system(f"{nickname} left the chat")
    
    except Exception as e:
        logger.error(f"Error in WebSocket for {nickname}: {e}")
        room.remove_user(websocket)
        await websocket.close(code=1011, reason="Internal server error")

@app.get("/rooms/{room_id}/history")
async def get_room_history(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = rooms[room_id]
    return JSONResponse(content=room.history)

@app.get("/rooms/{room_id}/users")
async def get_room_users(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = rooms[room_id]
    users = list(room.nicknames.values())
    return JSONResponse(content=users)

@app.get("/")
async def root():
    return {
        "message": "WebSocket Chat Server",
        "endpoints": {
            "websocket": "/ws/{room_id}?nickname={name}",
            "history": "/rooms/{room_id}/history",
            "users": "/rooms/{room_id}/users"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)