from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import Dict, List
import json

app = FastAPI()

class Room:
    def __init__(self, name: str):
        self.name = name
        self.connections: List[WebSocket] = []
        self.users: Dict[WebSocket, str] = {}
        self.message_history: List[dict] = []
        self.max_history = 50

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.remove(websocket)
        if websocket in self.users:
            del self.users[websocket]

    def set_nickname(self, websocket: WebSocket, nickname: str):
        self.users[websocket] = nickname

    async def broadcast(self, message: dict, exclude: WebSocket = None):
        for conn in self.connections:
            if conn != exclude:
                try:
                    await conn.send_text(json.dumps(message))
                except:
                    pass

    def add_message(self, message: dict):
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)

    def get_user_count(self) -> int:
        return len(self.connections)


rooms: Dict[str, Room] = {}


def get_or_create_room(room_name: str) -> Room:
    if room_name not in rooms:
        rooms[room_name] = Room(room_name)
    return rooms[room_name]


@app.get("/rooms")
async def list_rooms():
    return {
        "rooms": [
            {
                "name": room.name,
                "user_count": room.get_user_count()
            }
            for room in rooms.values()
        ]
    }


@app.websocket("/ws/{room_name}")
async def websocket_endpoint(websocket: WebSocket, room_name: str):
    room = get_or_create_room(room_name)
    await room.connect(websocket)
    
    nickname = None
    
    try:
        # Wait for nickname as first message
        data = await websocket.receive_text()
        try:
            msg = json.loads(data)
            if msg.get("type") == "nickname":
                nickname = msg.get("nickname", "Anonymous")
                room.set_nickname(websocket, nickname)
                
                # Send message history
                for hist_msg in room.message_history:
                    await websocket.send_text(json.dumps(hist_msg))
                
                # Broadcast join message
                join_msg = {
                    "type": "system",
                    "message": f"{nickname} joined the room"
                }
                await room.broadcast(join_msg)
                room.add_message(join_msg)
        except json.JSONDecodeError:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Invalid message format. Please send nickname first."
            }))
            await websocket.close()
            return
        
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                
                if msg.get("type") == "message":
                    chat_msg = {
                        "type": "message",
                        "nickname": room.users.get(websocket, "Anonymous"),
                        "message": msg.get("message", ""),
                        "room": room_name
                    }
                    await room.broadcast(chat_msg)
                    room.add_message(chat_msg)
                    
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid message format"
                }))
                
    except WebSocketDisconnect:
        room.disconnect(websocket)
        
        if nickname:
            leave_msg = {
                "type": "system",
                "message": f"{nickname} left the room"
            }
            await room.broadcast(leave_msg)
            room.add_message(leave_msg)
        
        # Clean up empty rooms
        if room.get_user_count() == 0 and room_name in rooms:
            del rooms[room_name]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
