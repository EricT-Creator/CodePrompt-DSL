from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import json
import time

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, Set[WebSocket]] = {}
        self.message_history: Dict[str, List[Dict]] = {}
        self.max_history = 100

    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
            self.message_history[room_id] = []
        self.rooms[room_id].add(websocket)
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "system",
            "message": f"Connected to room {room_id}",
            "timestamp": time.time()
        })
        
        # Send recent history
        for msg in self.message_history[room_id][-10:]:
            await websocket.send_json(msg)

    def disconnect(self, websocket: WebSocket, room_id: str):
        if room_id in self.rooms:
            self.rooms[room_id].discard(websocket)
            if not self.rooms[room_id]:
                del self.rooms[room_id]
                del self.message_history[room_id]

    async def broadcast(self, message: Dict, room_id: str, sender: WebSocket = None):
        if room_id not in self.rooms:
            return
        
        # Store in history
        self.message_history[room_id].append(message)
        if len(self.message_history[room_id]) > self.max_history:
            self.message_history[room_id] = self.message_history[room_id][-self.max_history:]
        
        # Broadcast to all connections in room
        for connection in self.rooms[room_id]:
            if connection != sender:
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await manager.connect(websocket, room_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                message_type = message.get("type", "message")
                
                if message_type == "message":
                    chat_message = {
                        "type": "chat",
                        "user": message.get("user", "anonymous"),
                        "content": message.get("content", ""),
                        "timestamp": time.time()
                    }
                    await manager.broadcast(chat_message, room_id, sender=websocket)
                    
                elif message_type == "join":
                    join_msg = {
                        "type": "system",
                        "message": f"{message.get('user', 'anonymous')} joined the room",
                        "timestamp": time.time()
                    }
                    await manager.broadcast(join_msg, room_id, sender=websocket)
                    
                elif message_type == "leave":
                    leave_msg = {
                        "type": "system", 
                        "message": f"{message.get('user', 'anonymous')} left the room",
                        "timestamp": time.time()
                    }
                    await manager.broadcast(leave_msg, room_id, sender=websocket)
                    
            except json.JSONDecodeError:
                error_msg = {"type": "error", "message": "Invalid JSON format"}
                await websocket.send_json(error_msg)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
        leave_msg = {
            "type": "system",
            "message": "A user disconnected",
            "timestamp": time.time()
        }
        await manager.broadcast(leave_msg, room_id)

@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": time.time()}

@app.get("/rooms/{room_id}/history")
async def get_history(room_id: str):
    if room_id in manager.message_history:
        return {
            "room_id": room_id,
            "message_count": len(manager.message_history[room_id]),
            "history": manager.message_history[room_id][-20:]
        }
    return {"room_id": room_id, "message_count": 0, "history": []}

@app.get("/rooms/{room_id}/connections")
async def get_connections(room_id: str):
    if room_id in manager.rooms:
        return {
            "room_id": room_id,
            "connection_count": len(manager.rooms[room_id])
        }
    return {"room_id": room_id, "connection_count": 0}