import asyncio
import json
import time
from collections import defaultdict
from typing import Dict, List, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

app = FastAPI(title="WebSocket Chat Server")

# Data structures
class ChatRoom:
    def __init__(self, name: str):
        self.name = name
        self.connections: Set[WebSocket] = set()
        self.history: List[Dict] = []
        self.max_history = 50
        self.user_counts = defaultdict(int)  # username -> count
    
    def add_connection(self, websocket: WebSocket, nickname: str):
        self.connections.add(websocket)
        self.user_counts[nickname] += 1
        
        # Add join message to history
        join_message = {
            "type": "system",
            "content": f"{nickname} joined the room",
            "timestamp": int(time.time()),
            "room": self.name,
        }
        self.history.append(join_message)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def remove_connection(self, websocket: WebSocket, nickname: str):
        if websocket in self.connections:
            self.connections.remove(websocket)
            self.user_counts[nickname] -= 1
            if self.user_counts[nickname] <= 0:
                del self.user_counts[nickname]
            
            # Add leave message to history
            leave_message = {
                "type": "system",
                "content": f"{nickname} left the room",
                "timestamp": int(time.time()),
                "room": self.name,
            }
            self.history.append(leave_message)
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]
    
    def broadcast(self, message: Dict):
        """Broadcast message to all connected clients"""
        message_json = json.dumps(message)
        
        # Iterate through connections and send
        disconnected = []
        for connection in self.connections:
            try:
                asyncio.create_task(connection.send_text(message_json))
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.connections.remove(connection)
    
    def add_message(self, message: Dict):
        """Add message to history and broadcast"""
        self.history.append(message)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
        self.broadcast(message)
    
    def get_user_count(self) -> int:
        """Get total number of unique users in room"""
        return len(self.user_counts)

# Global rooms store
rooms: Dict[str, ChatRoom] = defaultdict(lambda: None)
rooms["general"] = ChatRoom("general")
rooms["tech"] = ChatRoom("tech")
rooms["random"] = ChatRoom("random")

class RoomInfo(BaseModel):
    name: str
    user_count: int

class UserInfo(BaseModel):
    nickname: str
    rooms: List[str]

# HTTP endpoints
@app.get("/")
async def root():
    return {"message": "WebSocket Chat Server", "status": "running"}

@app.get("/rooms", response_model=List[RoomInfo])
async def get_rooms():
    """Get list of all rooms with user counts"""
    room_list = []
    for room_name, room in rooms.items():
        if room is not None:
            room_list.append(RoomInfo(
                name=room_name,
                user_count=room.get_user_count()
            ))
    return room_list

@app.get("/room/{room_name}/history")
async def get_room_history(room_name: str):
    """Get chat history for a specific room"""
    room = rooms.get(room_name)
    if not room:
        return {"error": "Room not found"}
    
    return {
        "room": room_name,
        "history": room.history,
        "total_messages": len(room.history),
        "active_users": room.get_user_count(),
    }

# WebSocket endpoint
@app.websocket("/ws/{room_name}/{nickname}")
async def websocket_endpoint(websocket: WebSocket, room_name: str, nickname: str):
    await websocket.accept()
    
    # Get or create room
    if room_name not in rooms or rooms[room_name] is None:
        rooms[room_name] = ChatRoom(room_name)
    
    room = rooms[room_name]
    
    # Add connection to room
    room.add_connection(websocket, nickname)
    
    # Send welcome message with room info
    welcome_message = {
        "type": "system",
        "content": f"Welcome to {room_name}, {nickname}!",
        "timestamp": int(time.time()),
        "room": room_name,
        "user_count": room.get_user_count(),
        "history": room.history[-20:],  # Last 20 messages
    }
    await websocket.send_text(json.dumps(welcome_message))
    
    # Broadcast user join to room
    join_broadcast = {
        "type": "system",
        "content": f"{nickname} joined the room",
        "timestamp": int(time.time()),
        "room": room_name,
        "user_count": room.get_user_count(),
    }
    room.broadcast(join_broadcast)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Validate message structure
            if "content" not in message_data:
                error_message = {
                    "type": "error",
                    "content": "Invalid message format",
                    "timestamp": int(time.time()),
                }
                await websocket.send_text(json.dumps(error_message))
                continue
            
            # Create chat message
            chat_message = {
                "type": "chat",
                "sender": nickname,
                "content": message_data["content"],
                "timestamp": int(time.time()),
                "room": room_name,
            }
            
            # Add to room history and broadcast
            room.add_message(chat_message)
            
            # Also send to sender for confirmation
            await websocket.send_text(json.dumps({
                "type": "ack",
                "message_id": chat_message["timestamp"],
                "status": "delivered",
            }))
    
    except WebSocketDisconnect:
        # Handle disconnection
        room.remove_connection(websocket, nickname)
        
        # Broadcast user leave to room
        leave_broadcast = {
            "type": "system",
            "content": f"{nickname} left the room",
            "timestamp": int(time.time()),
            "room": room_name,
            "user_count": room.get_user_count(),
        }
        room.broadcast(leave_broadcast)
    
    except Exception as e:
        # Handle other exceptions
        room.remove_connection(websocket, nickname)
        
        # Broadcast error
        error_broadcast = {
            "type": "system",
            "content": f"{nickname} disconnected due to error",
            "timestamp": int(time.time()),
            "room": room_name,
        }
        room.broadcast(error_broadcast)

# Room cleanup task (optional)
async def cleanup_inactive_rooms():
    """Periodically clean up empty rooms (except default rooms)"""
    while True:
        await asyncio.sleep(300)  # Run every 5 minutes
        
        default_rooms = {"general", "tech", "random"}
        rooms_to_remove = []
        
        for room_name, room in rooms.items():
            if room is not None and room_name not in default_rooms:
                if len(room.connections) == 0 and len(room.history) == 0:
                    rooms_to_remove.append(room_name)
        
        for room_name in rooms_to_remove:
            del rooms[room_name]
        
        if rooms_to_remove:
            print(f"Cleaned up rooms: {rooms_to_remove}")

@app.on_event("startup")
async def startup_event():
    """Start cleanup task on startup"""
    asyncio.create_task(cleanup_inactive_rooms())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)