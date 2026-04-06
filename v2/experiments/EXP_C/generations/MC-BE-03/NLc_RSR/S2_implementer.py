import asyncio
import json
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel


# ==================== Data Models ====================

class ChatMessage(BaseModel):
    nickname: str
    content: str
    timestamp: str
    msg_type: str  # "user" or "system"


class RoomUsersResponse(BaseModel):
    room_id: str
    users: List[str]
    count: int


class RoomHistoryResponse(BaseModel):
    room_id: str
    messages: List[ChatMessage]
    count: int


class RoomsResponse(BaseModel):
    rooms: List[str]
    count: int


# ==================== Internal Data Classes ====================

@dataclass
class Room:
    connections: Dict[WebSocket, str] = field(default_factory=dict)
    history: deque = field(default_factory=lambda: deque(maxlen=100))


# ==================== Room Manager ====================

class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, Room] = {}
    
    def join(self, room_id: str, websocket: WebSocket, nickname: str):
        if room_id not in self.rooms:
            self.rooms[room_id] = Room()
        
        room = self.rooms[room_id]
        room.connections[websocket] = nickname
        
        # Create system message
        system_msg = ChatMessage(
            nickname="System",
            content=f"{nickname} joined the room",
            timestamp=time.strftime("%H:%M:%S"),
            msg_type="system"
        )
        
        # Add to history
        room.history.append(system_msg)
        
        return room
    
    def leave(self, room_id: str, websocket: WebSocket):
        if room_id not in self.rooms:
            return
        
        room = self.rooms[room_id]
        nickname = room.connections.pop(websocket, None)
        
        if nickname:
            # Create system message
            system_msg = ChatMessage(
                nickname="System",
                content=f"{nickname} left the room",
                timestamp=time.strftime("%H:%M:%S"),
                msg_type="system"
            )
            
            # Add to history
            room.history.append(system_msg)
        
        # Clean up empty room
        if not room.connections:
            del self.rooms[room_id]
    
    async def broadcast(self, room_id: str, message: ChatMessage, exclude_websocket: Optional[WebSocket] = None):
        if room_id not in self.rooms:
            return
        
        room = self.rooms[room_id]
        disconnected = []
        
        # Convert message to JSON
        message_json = json.dumps({
            "nickname": message.nickname,
            "content": message.content,
            "timestamp": message.timestamp,
            "msg_type": message.msg_type
        })
        
        # Broadcast to all connections except the sender
        for websocket, _ in room.connections.items():
            if websocket is exclude_websocket:
                continue
            
            try:
                await websocket.send_text(message_json)
            except Exception:
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for websocket in disconnected:
            self.leave(room_id, websocket)
    
    def get_users(self, room_id: str) -> List[str]:
        if room_id not in self.rooms:
            return []
        
        room = self.rooms[room_id]
        return list(room.connections.values())
    
    def get_history(self, room_id: str) -> List[ChatMessage]:
        if room_id not in self.rooms:
            return []
        
        room = self.rooms[room_id]
        return list(room.history)
    
    def get_rooms(self) -> List[str]:
        return list(self.rooms.keys())


# ==================== FastAPI Application ====================

app = FastAPI(title="WebSocket Chat Server")
room_manager = RoomManager()


# ==================== WebSocket Handler ====================

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, nickname: str = "Anonymous"):
    await websocket.accept()
    
    # Join room
    room = room_manager.join(room_id, websocket, nickname)
    
    try:
        # Send history to new connection
        history = room_manager.get_history(room_id)
        history_data = [
            {
                "nickname": msg.nickname,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "msg_type": msg.msg_type
            }
            for msg in history
        ]
        await websocket.send_text(json.dumps({"type": "history", "data": history_data}))
        
        # Broadcast join message
        join_message = ChatMessage(
            nickname="System",
            content=f"{nickname} joined the room",
            timestamp=time.strftime("%H:%M:%S"),
            msg_type="system"
        )
        await room_manager.broadcast(room_id, join_message, exclude_websocket=websocket)
        
        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Validate message
                if not isinstance(message_data, dict) or "content" not in message_data:
                    continue
                
                content = message_data["content"].strip()
                if not content:
                    continue
                
                # Create chat message
                chat_message = ChatMessage(
                    nickname=nickname,
                    content=content,
                    timestamp=time.strftime("%H:%M:%S"),
                    msg_type="user"
                )
                
                # Add to history
                room.history.append(chat_message)
                
                # Broadcast to all other clients
                await room_manager.broadcast(room_id, chat_message, exclude_websocket=websocket)
            
            except json.JSONDecodeError:
                # Send error to client
                error_msg = json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
                await websocket.send_text(error_msg)
            
            except Exception as e:
                print(f"Error processing message: {e}")
                break
    
    except WebSocketDisconnect:
        # Client disconnected
        pass
    
    finally:
        # Leave room
        room_manager.leave(room_id, websocket)


# ==================== REST Endpoints ====================

@app.get("/rooms/{room_id}/users", response_model=RoomUsersResponse)
async def get_room_users(room_id: str):
    users = room_manager.get_users(room_id)
    return RoomUsersResponse(
        room_id=room_id,
        users=users,
        count=len(users)
    )


@app.get("/rooms/{room_id}/history", response_model=RoomHistoryResponse)
async def get_room_history(room_id: str):
    messages = room_manager.get_history(room_id)
    return RoomHistoryResponse(
        room_id=room_id,
        messages=messages,
        count=len(messages)
    )


@app.get("/rooms", response_model=RoomsResponse)
async def list_rooms():
    rooms = room_manager.get_rooms()
    return RoomsResponse(
        rooms=rooms,
        count=len(rooms)
    )


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "rooms_count": len(room_manager.rooms),
        "total_connections": sum(len(room.connections) for room in room_manager.rooms.values())
    }


# ==================== Demo Endpoints ====================

class CreateRoomRequest(BaseModel):
    room_id: str


@app.post("/demo/create_room")
async def create_demo_room(request: CreateRoomRequest):
    # Just accessing the room will create it
    if request.room_id not in room_manager.rooms:
        room_manager.rooms[request.room_id] = Room()
    
    return {"message": f"Room '{request.room_id}' created or already exists"}


@app.get("/demo/stats")
async def get_demo_stats():
    stats = {
        "total_rooms": len(room_manager.rooms),
        "rooms": {}
    }
    
    for room_id, room in room_manager.rooms.items():
        stats["rooms"][room_id] = {
            "users": len(room.connections),
            "history_count": len(room.history),
            "user_list": list(room.connections.values())
        }
    
    return stats


# ==================== Main Execution ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)