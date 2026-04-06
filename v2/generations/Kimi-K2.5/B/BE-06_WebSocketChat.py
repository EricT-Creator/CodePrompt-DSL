from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, Set, List
import json
import asyncio

app = FastAPI()

# In-memory storage
class Room:
    def __init__(self, name: str):
        self.name = name
        self.connections: Set[WebSocket] = set()
        self.history: List[Dict] = []
        self.max_history = 50
        self.nicknames: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, nickname: str):
        await websocket.accept()
        self.connections.add(websocket)
        self.nicknames[websocket] = nickname
        # Send history to new user
        for msg in self.history:
            await websocket.send_json(msg)
        # Broadcast join message
        await self.broadcast({
            "type": "system",
            "content": f"{nickname} joined the room",
            "room": self.name
        }, exclude=websocket)

    def disconnect(self, websocket: WebSocket):
        nickname = self.nicknames.pop(websocket, "Unknown")
        self.connections.discard(websocket)
        return nickname

    async def broadcast(self, message: Dict, exclude: WebSocket = None):
        # Add to history
        self.history.append(message)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        
        # Broadcast to all connections via set iteration
        disconnected = set()
        for conn in self.connections:
            if conn != exclude:
                try:
                    await conn.send_json(message)
                except Exception:
                    disconnected.add(conn)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.connections.discard(conn)
            self.nicknames.pop(conn, None)

    def get_user_count(self) -> int:
        return len(self.connections)

    def get_nicknames(self) -> List[str]:
        return list(self.nicknames.values())


# Room manager
rooms: Dict[str, Room] = {}


def get_or_create_room(room_name: str) -> Room:
    if room_name not in rooms:
        rooms[room_name] = Room(room_name)
    return rooms[room_name]


@app.get("/rooms")
async def list_rooms():
    """Get list of all rooms with user counts."""
    return {
        "rooms": [
            {
                "name": room.name,
                "user_count": room.get_user_count(),
                "users": room.get_nicknames()
            }
            for room in rooms.values()
        ]
    }


@app.websocket("/ws/{room_name}")
async def websocket_endpoint(websocket: WebSocket, room_name: str):
    """WebSocket endpoint for chat."""
    # Get nickname from query params or use default
    nickname = websocket.query_params.get("nickname", f"User_{id(websocket)}")
    
    room = get_or_create_room(room_name)
    await room.connect(websocket, nickname)
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                message_data = {"content": data}
            
            # Broadcast message to room
            await room.broadcast({
                "type": "message",
                "nickname": nickname,
                "content": message_data.get("content", ""),
                "room": room_name
            })
            
    except WebSocketDisconnect:
        # Handle disconnect
        nickname = room.disconnect(websocket)
        if room.get_user_count() == 0:
            # Clean up empty rooms
            del rooms[room_name]
        else:
            # Broadcast leave message
            await room.broadcast({
                "type": "system",
                "content": f"{nickname} left the room",
                "room": room_name
            })


@app.get("/")
async def root():
    return {
        "message": "WebSocket Chat Server",
        "endpoints": {
            "rooms": "GET /rooms - List all rooms",
            "websocket": "WS /ws/{room_name}?nickname=YourName - Connect to chat"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
