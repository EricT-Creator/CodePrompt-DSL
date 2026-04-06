from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import json
from datetime import datetime
from typing import Dict, Set, List, Optional
import uvicorn

app = FastAPI()

# Global room storage
class ChatRoom:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.active_connections: Set[WebSocket] = set()
        self.user_map: Dict[WebSocket, str] = {}
        self.message_log: List[Dict] = []

rooms: Dict[str, ChatRoom] = {}

def ensure_room(room_id: str) -> ChatRoom:
    """Get existing room or create new one"""
    if room_id not in rooms:
        rooms[room_id] = ChatRoom(room_id)
    return rooms[room_id]

async def send_to_room(room: ChatRoom, sender: str, content: str, is_system: bool = False):
    """Send a message to all users in a room"""
    message = {
        "sender": "system" if is_system else sender,
        "text": content,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    # Create a copy of connections to avoid mutation issues
    connections_copy = list(room.active_connections)
    failed_conns = []
    
    for ws in connections_copy:
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            failed_conns.append(ws)
    
    # Remove failed connections
    for ws in failed_conns:
        room.active_connections.discard(ws)
        if ws in room.user_map:
            del room.user_map[ws]
    
    # Store message if not a system message
    if not is_system:
        room.message_log.append(message)
        # Keep only last 100 messages
        if len(room.message_log) > 100:
            room.message_log = room.message_log[-100:]
    
    return message

@app.websocket("/ws/{room_id}")
async def chat_websocket(websocket: WebSocket, room_id: str):
    """WebSocket endpoint for real-time chat"""
    # Validate parameters
    nickname = websocket.query_params.get("nickname", "").strip()
    if not nickname or not room_id:
        await websocket.close(code=1008, reason="nickname and room_id required")
        return
    
    # Accept connection
    await websocket.accept()
    
    # Get or create room
    room = ensure_room(room_id)
    room.active_connections.add(websocket)
    room.user_map[websocket] = nickname
    
    # Notify room about new user
    await send_to_room(room, nickname, f"{nickname} joined the chat", is_system=True)
    
    try:
        # Main message handling loop
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            # Broadcast to all users in the room
            await send_to_room(room, nickname, data)
            
    except WebSocketDisconnect:
        # Handle disconnection
        if websocket in room.active_connections:
            room.active_connections.discard(websocket)
        
        if websocket in room.user_map:
            user_name = room.user_map[websocket]
            del room.user_map[websocket]
            
            # Notify room about user leaving
            if room.active_connections:
                await send_to_room(room, user_name, f"{user_name} left the chat", is_system=True)
        
        # Clean up empty rooms
        if not room.active_connections:
            del rooms[room_id]
    
    except Exception as e:
        # Handle unexpected errors
        if websocket in room.active_connections:
            room.active_connections.discard(websocket)
        if websocket in room.user_map:
            del room.user_map[websocket]
        await websocket.close(code=1011, reason=f"Error: {str(e)}")

@app.get("/rooms/{room_id}/users")
async def get_users_in_room(room_id: str):
    """Get list of users in a specific room"""
    if room_id not in rooms:
        return JSONResponse(
            status_code=404,
            content={"error": f"Room '{room_id}' does not exist"}
        )
    
    room = rooms[room_id]
    users = list(room.user_map.values())
    return {
        "room_id": room_id,
        "users": users,
        "user_count": len(users)
    }

@app.get("/rooms/{room_id}/history")
async def get_message_history(room_id: str):
    """Get message history for a room"""
    if room_id not in rooms:
        return JSONResponse(
            status_code=404,
            content={"error": f"Room '{room_id}' not found"}
        )
    
    room = rooms[room_id]
    return {
        "room_id": room_id,
        "history": room.message_log,
        "total_messages": len(room.message_log)
    }

@app.get("/rooms")
async def list_all_rooms():
    """List all active chat rooms"""
    room_data = []
    for room_id, room in rooms.items():
        room_data.append({
            "room_id": room_id,
            "active_users": len(room.user_map),
            "total_messages": len(room.message_log),
            "users": list(room.user_map.values())
        })
    
    return {"rooms": room_data, "total_rooms": len(rooms)}

@app.get("/")
async def server_info():
    """Server information endpoint"""
    return {
        "server": "FastAPI WebSocket Chat Server",
        "description": "Real-time chat with room-based WebSocket connections",
        "version": "1.0",
        "endpoints": {
            "websocket": "ws://<host>/ws/{room_id}?nickname={name}",
            "room_users": "GET /rooms/{room_id}/users",
            "room_history": "GET /rooms/{room_id}/history",
            "list_rooms": "GET /rooms"
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)