from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import json
from datetime import datetime
from typing import Dict, Set, List
import uvicorn

app = FastAPI(title="WebSocket Chat Server")

# Room management
rooms: Dict[str, "Room"] = {}

class Room:
    """Represents a chat room with active connections and message history"""
    def __init__(self):
        self.connections: Set[WebSocket] = set()
        self.nicknames: Dict[WebSocket, str] = {}
        self.message_history: List[Dict] = []

def get_or_create_room(room_id: str) -> Room:
    """Retrieve existing room or create a new one"""
    if room_id not in rooms:
        rooms[room_id] = Room()
    return rooms[room_id]

async def broadcast_to_room(room: Room, sender_nickname: str, message_content: str, is_system: bool = False):
    """Send a message to all active connections in a room"""
    message_payload = {
        "sender": "system" if is_system else sender_nickname,
        "text": message_content,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    # Work with a copy to avoid modification during iteration
    connections_copy = list(room.connections)
    broken_connections = []
    
    for ws in connections_copy:
        try:
            await ws.send_text(json.dumps(message_payload))
        except Exception:
            broken_connections.append(ws)
    
    # Clean up broken connections
    for ws in broken_connections:
        room.connections.discard(ws)
        if ws in room.nicknames:
            del room.nicknames[ws]
    
    # Store user messages in history
    if not is_system:
        room.message_history.append(message_payload)
        # Keep only last 100 messages
        if len(room.message_history) > 100:
            room.message_history = room.message_history[-100:]
    
    return message_payload

@app.websocket("/ws/{room_id}")
async def websocket_chat_endpoint(websocket: WebSocket, room_id: str):
    """Handle WebSocket connections for chat rooms"""
    # Validate input parameters
    nickname = websocket.query_params.get("nickname", "").strip()
    if not nickname or not room_id:
        await websocket.close(code=1008, reason="Nickname and room_id are required")
        return
    
    # Accept the WebSocket connection
    await websocket.accept()
    
    # Get or create the room
    room = get_or_create_room(room_id)
    room.connections.add(websocket)
    room.nicknames[websocket] = nickname
    
    # Notify room about new user
    await broadcast_to_room(room, nickname, f"{nickname} joined the chat", is_system=True)
    
    try:
        # Main message processing loop
        while True:
            # Wait for messages from this client
            user_message = await websocket.receive_text()
            
            # Broadcast the message to everyone in the room
            await broadcast_to_room(room, nickname, user_message)
    
    except WebSocketDisconnect:
        # Handle client disconnection
        if websocket in room.connections:
            room.connections.discard(websocket)
        
        if websocket in room.nicknames:
            disconnected_user = room.nicknames[websocket]
            del room.nicknames[websocket]
            
            # Notify remaining users about the departure
            if room.connections:
                await broadcast_to_room(room, disconnected_user, f"{disconnected_user} left the chat", is_system=True)
        
        # Clean up empty rooms
        if not room.connections:
            del rooms[room_id]
    
    except Exception as e:
        # Handle unexpected errors
        if websocket in room.connections:
            room.connections.discard(websocket)
        if websocket in room.nicknames:
            del room.nicknames[websocket]
        await websocket.close(code=1011, reason=f"Unexpected error: {str(e)}")

@app.get("/rooms/{room_id}/users")
async def get_room_users_endpoint(room_id: str):
    """Get list of users currently in a room"""
    if room_id not in rooms:
        return JSONResponse(
            status_code=404,
            content={"error": f"Room '{room_id}' does not exist"}
        )
    
    room = rooms[room_id]
    user_list = list(room.nicknames.values())
    return {
        "room_id": room_id,
        "users": user_list,
        "user_count": len(user_list)
    }

@app.get("/rooms/{room_id}/history")
async def get_room_history_endpoint(room_id: str):
    """Get message history for a room"""
    if room_id not in rooms:
        return JSONResponse(
            status_code=404,
            content={"error": f"Room '{room_id}' not found"}
        )
    
    room = rooms[room_id]
    return {
        "room_id": room_id,
        "history": room.message_history,
        "message_count": len(room.message_history)
    }

@app.get("/rooms")
async def list_rooms_endpoint():
    """List all active chat rooms"""
    room_summary = []
    for room_id, room in rooms.items():
        room_summary.append({
            "room_id": room_id,
            "active_users": len(room.nicknames),
            "total_messages": len(room.message_history),
            "user_names": list(room.nicknames.values())
        })
    
    return {
        "rooms": room_summary,
        "total_rooms": len(rooms)
    }

@app.get("/")
async def server_root_endpoint():
    """Server information and documentation"""
    return {
        "server": "FastAPI WebSocket Chat Server",
        "description": "Real-time chat application with room-based WebSocket connections",
        "websocket_endpoint": "ws://<host>/ws/{room_id}?nickname={your_name}",
        "rest_endpoints": {
            "get_room_users": "GET /rooms/{room_id}/users",
            "get_room_history": "GET /rooms/{room_id}/history",
            "list_all_rooms": "GET /rooms"
        },
        "features": [
            "Real-time messaging via WebSockets",
            "Room-based chat organization",
            "Message history (last 100 messages per room)",
            "User presence tracking",
            "No external dependencies beyond FastAPI/uvicorn"
        ]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)