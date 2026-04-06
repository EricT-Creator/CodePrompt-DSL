from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, Set, List
import json
import time
from datetime import datetime

app = FastAPI()

class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, Dict] = {}
    
    def create_room(self, room_id: str):
        self.rooms[room_id] = {
            "connections": set(),
            "nicknames": {},
            "history": [],
            "max_history": 100
        }
    
    def add_connection(self, room_id: str, websocket: WebSocket, nickname: str):
        if room_id not in self.rooms:
            self.create_room(room_id)
        
        room = self.rooms[room_id]
        room["connections"].add(websocket)
        room["nicknames"][websocket] = nickname
    
    def remove_connection(self, room_id: str, websocket: WebSocket):
        if room_id in self.rooms:
            room = self.rooms[room_id]
            room["connections"].discard(websocket)
            if websocket in room["nicknames"]:
                del room["nicknames"][websocket]
            
            # Clean up empty room
            if not room["connections"]:
                del self.rooms[room_id]
    
    def add_message(self, room_id: str, message: Dict):
        if room_id in self.rooms:
            room = self.rooms[room_id]
            room["history"].append(message)
            if len(room["history"]) > room["max_history"]:
                room["history"] = room["history"][-room["max_history"]:]
    
    def get_room_users(self, room_id: str) -> List[str]:
        if room_id in self.rooms:
            return list(self.rooms[room_id]["nicknames"].values())
        return []
    
    def get_room_history(self, room_id: str) -> List[Dict]:
        if room_id in self.rooms:
            return self.rooms[room_id]["history"]
        return []
    
    async def broadcast(self, room_id: str, message: Dict, exclude: WebSocket = None):
        if room_id not in self.rooms:
            return
        
        room = self.rooms[room_id]
        connections = list(room["connections"])
        
        for connection in connections:
            if connection != exclude:
                try:
                    await connection.send_json(message)
                except:
                    # Remove dead connection
                    self.remove_connection(room_id, connection)

manager = RoomManager()

@app.websocket("/ws/{room_id}")
async def websocket_chat(websocket: WebSocket, room_id: str, nickname: str = "Guest"):
    # Validate inputs
    if not room_id or not nickname:
        await websocket.close(code=1008, reason="Room ID and nickname required")
        return
    
    # Accept connection
    await websocket.accept()
    
    # Register connection
    manager.add_connection(room_id, websocket, nickname)
    
    # Send connection confirmation
    await websocket.send_json({
        "type": "system",
        "room_id": room_id,
        "message": f"Connected as '{nickname}'",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Broadcast join notification
    join_msg = {
        "type": "join",
        "user": nickname,
        "room_id": room_id,
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.broadcast(room_id, join_msg, exclude=websocket)
    
    # Send recent history
    history = manager.get_room_history(room_id)
    for msg in history[-15:]:
        await websocket.send_json(msg)
    
    # Message loop
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                msg_type = message_data.get("type", "chat")
                
                if msg_type == "chat":
                    content = message_data.get("content", "")
                    if content:
                        chat_msg = {
                            "type": "message",
                            "sender": nickname,
                            "content": content,
                            "timestamp": datetime.utcnow().isoformat(),
                            "room_id": room_id
                        }
                        
                        # Store in history
                        manager.add_message(room_id, chat_msg)
                        
                        # Broadcast to room
                        await manager.broadcast(room_id, chat_msg, exclude=websocket)
                
                elif msg_type == "typing":
                    typing_msg = {
                        "type": "typing",
                        "user": nickname,
                        "is_typing": message_data.get("is_typing", False),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await manager.broadcast(room_id, typing_msg, exclude=websocket)
                
                elif msg_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid message format"
                })
                
    except WebSocketDisconnect:
        # Handle disconnect
        manager.remove_connection(room_id, websocket)
        
        # Broadcast leave notification
        leave_msg = {
            "type": "leave",
            "user": nickname,
            "room_id": room_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        await manager.broadcast(room_id, leave_msg)

@app.get("/rooms/{room_id}/users")
async def list_users(room_id: str):
    users = manager.get_room_users(room_id)
    return {
        "room_id": room_id,
        "users": users,
        "user_count": len(users)
    }

@app.get("/rooms/{room_id}/history")
async def get_message_history(room_id: str, limit: int = 20):
    history = manager.get_room_history(room_id)
    return {
        "room_id": room_id,
        "total_messages": len(history),
        "messages": history[-limit:] if limit > 0 else history
    }

@app.get("/rooms")
async def list_rooms():
    rooms = []
    for room_id, room_data in manager.rooms.items():
        rooms.append({
            "room_id": room_id,
            "user_count": len(room_data["connections"]),
            "message_count": len(room_data["history"])
        })
    return {"rooms": rooms}

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "server_time": datetime.utcnow().isoformat(),
        "active_rooms": len(manager.rooms)
    }