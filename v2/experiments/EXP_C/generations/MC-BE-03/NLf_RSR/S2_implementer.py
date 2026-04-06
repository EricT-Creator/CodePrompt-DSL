from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from typing import Dict, Set, List, Optional
import json
import uuid
import time
from datetime import datetime
from dataclasses import dataclass

app = FastAPI(title="WebSocket Chat Server")

# ===================== Data Models =====================

@dataclass
class UserInfo:
    nickname: str
    room_id: str
    connected_at: float

@dataclass
class Message:
    id: str
    room_id: str
    nickname: str
    content: str
    timestamp: float
    message_type: str  # "user" or "system"

class ClientMessage(BaseModel):
    content: str

class RoomInfo(BaseModel):
    room_id: str
    online_count: int
    users: List[str]

# ===================== State Management =====================

class ChatManager:
    def __init__(self):
        self.rooms: Dict[str, Set[WebSocket]] = {}
        self.user_info: Dict[WebSocket, UserInfo] = {}
        self.message_history: Dict[str, List[Message]] = {}
        self.MAX_HISTORY = 100
    
    def create_room(self, room_id: str):
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
            self.message_history[room_id] = []
    
    def add_user(self, websocket: WebSocket, room_id: str, nickname: str):
        self.create_room(room_id)
        self.rooms[room_id].add(websocket)
        self.user_info[websocket] = UserInfo(
            nickname=nickname,
            room_id=room_id,
            connected_at=time.time()
        )
    
    def remove_user(self, websocket: WebSocket):
        if websocket not in self.user_info:
            return
        
        user_info = self.user_info[websocket]
        room_id = user_info.room_id
        
        if room_id in self.rooms:
            self.rooms[room_id].discard(websocket)
            
            # Clean up empty rooms
            if not self.rooms[room_id]:
                del self.rooms[room_id]
                if room_id in self.message_history:
                    del self.message_history[room_id]
        
        if websocket in self.user_info:
            del self.user_info[websocket]
    
    def add_message(self, room_id: str, nickname: str, content: str, message_type: str = "user"):
        if room_id not in self.message_history:
            self.message_history[room_id] = []
        
        message = Message(
            id=str(uuid.uuid4()),
            room_id=room_id,
            nickname=nickname,
            content=content,
            timestamp=time.time(),
            message_type=message_type
        )
        
        history = self.message_history[room_id]
        history.append(message)
        
        # Enforce history cap
        if len(history) > self.MAX_HISTORY:
            self.message_history[room_id] = history[-self.MAX_HISTORY:]
        
        return message
    
    def get_room_users(self, room_id: str) -> List[str]:
        if room_id not in self.rooms:
            return []
        
        users = []
        for ws in self.rooms[room_id]:
            if ws in self.user_info:
                users.append(self.user_info[ws].nickname)
        return users
    
    def get_message_history(self, room_id: str, limit: int = 100) -> List[Message]:
        if room_id not in self.message_history:
            return []
        
        history = self.message_history[room_id]
        return history[-limit:]
    
    async def broadcast(self, room_id: str, message: Message):
        """Broadcast message to all users in room by iterating connections"""
        if room_id not in self.rooms:
            return
        
        stale_connections = set()
        message_dict = {
            "id": message.id,
            "room_id": message.room_id,
            "nickname": message.nickname,
            "content": message.content,
            "timestamp": message.timestamp,
            "type": message.message_type,
            "formatted_time": datetime.fromtimestamp(message.timestamp).isoformat()
        }
        
        for ws in self.rooms[room_id]:
            try:
                await ws.send_json(message_dict)
            except Exception:
                stale_connections.add(ws)
        
        # Clean up stale connections
        for ws in stale_connections:
            self.rooms[room_id].discard(ws)
            if ws in self.user_info:
                del self.user_info[ws]

# ===================== Global Instance =====================

chat_manager = ChatManager()

# ===================== WebSocket Endpoint =====================

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, nickname: str = "Anonymous"):
    await websocket.accept()
    
    # Register user
    chat_manager.add_user(websocket, room_id, nickname)
    
    # Send welcome message
    welcome_message = chat_manager.add_message(
        room_id,
        "system",
        f"User '{nickname}' joined the room",
        "system"
    )
    await chat_manager.broadcast(room_id, welcome_message)
    
    # Send recent history
    history = chat_manager.get_message_history(room_id, 20)
    for message in history:
        try:
            await websocket.send_json({
                "id": message.id,
                "room_id": message.room_id,
                "nickname": message.nickname,
                "content": message.content,
                "timestamp": message.timestamp,
                "type": message.message_type,
                "formatted_time": datetime.fromtimestamp(message.timestamp).isoformat()
            })
        except Exception:
            break
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                content = message_data.get("content", "").strip()
                
                if not content:
                    continue
                
                if len(content) > 1000:
                    await websocket.send_json({
                        "error": "Message too long (max 1000 characters)"
                    })
                    continue
                
                # Add message to history and broadcast
                user_info = chat_manager.user_info[websocket]
                message = chat_manager.add_message(
                    room_id,
                    user_info.nickname,
                    content,
                    "user"
                )
                await chat_manager.broadcast(room_id, message)
                
            except json.JSONDecodeError:
                await websocket.send_json({
                    "error": "Invalid message format"
                })
            except Exception as e:
                await websocket.send_json({
                    "error": str(e)
                })
    
    except WebSocketDisconnect:
        # User disconnected
        if websocket in chat_manager.user_info:
            user_info = chat_manager.user_info[websocket]
            
            # Send leave message
            leave_message = chat_manager.add_message(
                room_id,
                "system",
                f"User '{user_info.nickname}' left the room",
                "system"
            )
            await chat_manager.broadcast(room_id, leave_message)
        
        # Remove user
        chat_manager.remove_user(websocket)

# ===================== REST Endpoints =====================

@app.get("/rooms", response_model=List[RoomInfo])
async def list_rooms():
    rooms = []
    for room_id, connections in chat_manager.rooms.items():
        rooms.append(RoomInfo(
            room_id=room_id,
            online_count=len(connections),
            users=chat_manager.get_room_users(room_id)
        ))
    return rooms

@app.get("/rooms/{room_id}/users", response_model=List[str])
async def get_room_users(room_id: str):
    if room_id not in chat_manager.rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    return chat_manager.get_room_users(room_id)

@app.get("/rooms/{room_id}/history")
async def get_room_history(room_id: str, limit: int = 50):
    if room_id not in chat_manager.message_history:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if limit > 100:
        limit = 100
    
    history = chat_manager.get_message_history(room_id, limit)
    return [
        {
            "id": msg.id,
            "room_id": msg.room_id,
            "nickname": msg.nickname,
            "content": msg.content,
            "timestamp": msg.timestamp,
            "type": msg.message_type,
            "formatted_time": datetime.fromtimestamp(msg.timestamp).isoformat()
        }
        for msg in history
    ]

@app.get("/rooms/{room_id}/stats")
async def get_room_stats(room_id: str):
    if room_id not in chat_manager.rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    return {
        "room_id": room_id,
        "online_count": len(chat_manager.rooms[room_id]),
        "total_messages": len(chat_manager.message_history.get(room_id, [])),
        "users": chat_manager.get_room_users(room_id)
    }

# ===================== Health Check =====================

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "total_rooms": len(chat_manager.rooms),
        "total_connections": sum(len(conns) for conns in chat_manager.rooms.values()),
        "total_users": len(chat_manager.user_info),
        "timestamp": time.time()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)