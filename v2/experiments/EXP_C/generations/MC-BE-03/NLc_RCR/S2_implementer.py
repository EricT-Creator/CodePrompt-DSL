import json
from collections import deque
from typing import Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

app = FastAPI()

class ChatMessage:
    def __init__(self, nickname: str, content: str, timestamp: str, msg_type: str = "user"):
        self.nickname = nickname
        self.content = content
        self.timestamp = timestamp
        self.msg_type = msg_type
    
    def to_dict(self):
        return {
            "nickname": self.nickname,
            "content": self.content,
            "timestamp": self.timestamp,
            "msg_type": self.msg_type
        }

class Room:
    def __init__(self):
        self.connections: Dict[WebSocket, str] = {}
        self.history: deque = deque(maxlen=100)
    
    async def broadcast(self, message: str, exclude: WebSocket = None):
        disconnected = []
        for ws, _ in self.connections.items():
            if ws != exclude:
                try:
                    await ws.send_text(message)
                except:
                    disconnected.append(ws)
        for ws in disconnected:
            if ws in self.connections:
                del self.connections[ws]

class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, Room] = {}
    
    def get_or_create_room(self, room_id: str) -> Room:
        if room_id not in self.rooms:
            self.rooms[room_id] = Room()
        return self.rooms[room_id]
    
    async def join(self, room_id: str, ws: WebSocket, nickname: str):
        room = self.get_or_create_room(room_id)
        room.connections[ws] = nickname
        
        join_msg = ChatMessage(
            nickname="System",
            content=f"{nickname} joined the room",
            timestamp=self._get_timestamp(),
            msg_type="system"
        )
        room.history.append(join_msg)
        await room.broadcast(json.dumps(join_msg.to_dict()))
        
        await ws.send_text(json.dumps([m.to_dict() for m in room.history]))
    
    async def leave(self, room_id: str, ws: WebSocket):
        if room_id not in self.rooms:
            return
        room = self.rooms[room_id]
        nickname = room.connections.get(ws)
        if nickname:
            del room.connections[ws]
            leave_msg = ChatMessage(
                nickname="System",
                content=f"{nickname} left the room",
                timestamp=self._get_timestamp(),
                msg_type="system"
            )
            room.history.append(leave_msg)
            await room.broadcast(json.dumps(leave_msg.to_dict()))
    
    async def broadcast(self, room_id: str, message: str, sender: WebSocket):
        if room_id not in self.rooms:
            return
        room = self.rooms[room_id]
        nickname = room.connections.get(sender, "Unknown")
        chat_msg = ChatMessage(
            nickname=nickname,
            content=message,
            timestamp=self._get_timestamp(),
            msg_type="user"
        )
        room.history.append(chat_msg)
        await room.broadcast(json.dumps(chat_msg.to_dict()), exclude=sender)
    
    def get_users(self, room_id: str) -> list:
        if room_id not in self.rooms:
            return []
        return list(self.rooms[room_id].connections.values())
    
    def get_history(self, room_id: str) -> list:
        if room_id not in self.rooms:
            return []
        return [m.to_dict() for m in self.rooms[room_id].history]
    
    def list_rooms(self) -> list:
        return list(self.rooms.keys())
    
    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()

room_manager = RoomManager()

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, nickname: str = "Anonymous"):
    await websocket.accept()
    await room_manager.join(room_id, websocket, nickname)
    
    try:
        while True:
            data = await websocket.receive_text()
            await room_manager.broadcast(room_id, data, websocket)
    except WebSocketDisconnect:
        await room_manager.leave(room_id, websocket)

@app.get("/rooms/{room_id}/users")
async def get_users(room_id: str):
    return {"users": room_manager.get_users(room_id)}

@app.get("/rooms/{room_id}/history")
async def get_history(room_id: str):
    return {"history": room_manager.get_history(room_id)}

@app.get("/rooms")
async def list_rooms():
    return {"rooms": room_manager.list_rooms()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
