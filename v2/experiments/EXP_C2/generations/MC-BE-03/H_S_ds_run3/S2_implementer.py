from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, Set, List
import json
import time
from datetime import datetime

app = FastAPI()

class ChatRoom:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.connections: Set[WebSocket] = set()
        self.nicknames: Dict[WebSocket, str] = {}
        self.history: List[Dict] = []
        self.max_history = 100

    def add_connection(self, websocket: WebSocket, nickname: str):
        self.connections.add(websocket)
        self.nicknames[websocket] = nickname

    def remove_connection(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.discard(websocket)
            if websocket in self.nicknames:
                del self.nicknames[websocket]

    def add_message(self, message: Dict):
        self.history.append(message)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

    def get_users(self) -> List[str]:
        return list(self.nicknames.values())

class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, ChatRoom] = {}

    def get_or_create_room(self, room_id: str) -> ChatRoom:
        if room_id not in self.rooms:
            self.rooms[room_id] = ChatRoom(room_id)
        return self.rooms[room_id]

    async def broadcast_to_room(self, message: Dict, room_id: str, exclude: WebSocket = None):
        if room_id in self.rooms:
            room = self.rooms[room_id]
            # Snapshot connections to avoid modification during iteration
            connections = list(room.connections)
            for connection in connections:
                if connection != exclude:
                    try:
                        await connection.send_json(message)
                    except:
                        # Remove dead connection
                        room.remove_connection(connection)

manager = ConnectionManager()

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, nickname: str = "anonymous"):
    # Accept connection
    await websocket.accept()
    
    # Get or create room
    room = manager.get_or_create_room(room_id)
    room.add_connection(websocket, nickname)
    
    # Send welcome message
    await websocket.send_json({
        "type": "system",
        "message": f"Welcome to room '{room_id}' as '{nickname}'",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Broadcast user joined
    join_message = {
        "type": "system",
        "message": f"{nickname} joined the room",
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.broadcast_to_room(join_message, room_id, exclude=websocket)
    
    # Send recent history
    for msg in room.history[-10:]:
        await websocket.send_json(msg)
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            try:
                payload = json.loads(data)
                message_type = payload.get("type", "message")
                content = payload.get("content", "")
                
                if message_type == "message":
                    chat_message = {
                        "type": "chat",
                        "sender": nickname,
                        "content": content,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    # Store in history
                    room.add_message(chat_message)
                    
                    # Broadcast to room
                    await manager.broadcast_to_room(chat_message, room_id, exclude=websocket)
                    
                elif message_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
                
    except WebSocketDisconnect:
        # Remove connection
        room.remove_connection(websocket)
        
        # Broadcast user left
        leave_message = {
            "type": "system",
            "message": f"{nickname} left the room",
            "timestamp": datetime.utcnow().isoformat()
        }
        await manager.broadcast_to_room(leave_message, room_id)
        
        # Clean up empty room
        if not room.connections:
            del manager.rooms[room_id]

@app.get("/rooms/{room_id}/users")
async def get_users(room_id: str):
    if room_id in manager.rooms:
        room = manager.rooms[room_id]
        return {
            "room_id": room_id,
            "users": room.get_users(),
            "user_count": len(room.connections)
        }
    return {"room_id": room_id, "users": [], "user_count": 0}

@app.get("/rooms/{room_id}/history")
async def get_history(room_id: str):
    if room_id in manager.rooms:
        room = manager.rooms[room_id]
        return {
            "room_id": room_id,
            "message_count": len(room.history),
            "history": room.history[-20:]
        }
    return {"room_id": room_id, "message_count": 0, "history": []}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_rooms": len(manager.rooms)
    }