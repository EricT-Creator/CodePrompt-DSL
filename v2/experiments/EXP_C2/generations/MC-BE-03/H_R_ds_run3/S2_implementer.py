from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import json
import asyncio
from datetime import datetime
from typing import Dict, Set, List
import uvicorn

app = FastAPI(title="WebSocket Chat Server")

# In-memory storage for rooms
class Room:
    def __init__(self):
        self.connections: Set[WebSocket] = set()
        self.nicknames: Dict[WebSocket, str] = {}
        self.history: List[Dict] = []

rooms: Dict[str, Room] = {}

def get_room(room_id: str) -> Room:
    """Get or create a room for the given room_id"""
    if room_id not in rooms:
        rooms[room_id] = Room()
    return rooms[room_id]

async def broadcast_message(room: Room, sender_nickname: str, message: str):
    """Broadcast a message to all connections in the room"""
    payload = {
        "sender": sender_nickname,
        "text": message,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    # Create a snapshot of connections to avoid mutation during iteration
    connections_snapshot = list(room.connections)
    dead_connections = []
    
    for ws in connections_snapshot:
        try:
            await ws.send_text(json.dumps(payload))
        except Exception:
            dead_connections.append(ws)
    
    # Clean up dead connections
    for ws in dead_connections:
        room.connections.discard(ws)
        if ws in room.nicknames:
            del room.nicknames[ws]
    
    # Add to history and cap at 100 messages
    room.history.append(payload)
    if len(room.history) > 100:
        room.history = room.history[-100:]
    
    return payload

async def broadcast_system_message(room: Room, message: str):
    """Broadcast a system message to all connections in the room"""
    payload = {
        "sender": "system",
        "text": message,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    connections_snapshot = list(room.connections)
    dead_connections = []
    
    for ws in connections_snapshot:
        try:
            await ws.send_text(json.dumps(payload))
        except Exception:
            dead_connections.append(ws)
    
    for ws in dead_connections:
        room.connections.discard(ws)
        if ws in room.nicknames:
            del room.nicknames[ws]

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    """WebSocket endpoint for chat connections"""
    # Get nickname from query parameter
    nickname = websocket.query_params.get("nickname", "").strip()
    
    # Validate parameters
    if not nickname or not room_id:
        await websocket.close(code=1008, reason="Missing nickname or room_id")
        return
    
    # Accept the WebSocket connection
    await websocket.accept()
    
    # Get the room
    room = get_room(room_id)
    
    # Register the connection
    room.connections.add(websocket)
    room.nicknames[websocket] = nickname
    
    # Broadcast join notification
    await broadcast_system_message(room, f"{nickname} has joined the chat")
    
    try:
        # Main message loop
        while True:
            # Receive message from client
            message = await websocket.receive_text()
            
            # Broadcast the message to all connections in the room
            await broadcast_message(room, nickname, message)
    
    except WebSocketDisconnect:
        # Handle disconnection
        room.connections.discard(websocket)
        if websocket in room.nicknames:
            del room.nicknames[websocket]
        
        # Broadcast leave notification if there are still connections
        if room.connections:
            await broadcast_system_message(room, f"{nickname} has left the chat")
        
        # Clean up empty room (optional)
        if not room.connections:
            del rooms[room_id]
    
    except Exception as e:
        # Handle any other exceptions
        room.connections.discard(websocket)
        if websocket in room.nicknames:
            del room.nicknames[websocket]
        await websocket.close(code=1011, reason=f"Server error: {str(e)}")

@app.get("/rooms/{room_id}/users")
async def get_room_users(room_id: str):
    """Get list of users currently in a room"""
    if room_id not in rooms:
        return JSONResponse(
            status_code=404,
            content={"error": f"Room '{room_id}' not found"}
        )
    
    room = rooms[room_id]
    users = list(room.nicknames.values())
    return {"room_id": room_id, "users": users, "count": len(users)}

@app.get("/rooms/{room_id}/history")
async def get_room_history(room_id: str):
    """Get message history for a room"""
    if room_id not in rooms:
        return JSONResponse(
            status_code=404,
            content={"error": f"Room '{room_id}' not found"}
        )
    
    room = rooms[room_id]
    return {"room_id": room_id, "history": room.history, "count": len(room.history)}

@app.get("/rooms")
async def list_rooms():
    """List all active rooms"""
    room_list = []
    for room_id, room in rooms.items():
        room_list.append({
            "room_id": room_id,
            "user_count": len(room.nicknames),
            "message_count": len(room.history)
        })
    return {"rooms": room_list}

@app.get("/")
async def root():
    """Root endpoint with server info"""
    return {
        "name": "WebSocket Chat Server",
        "description": "A real-time chat server using FastAPI WebSockets",
        "endpoints": {
            "websocket": "/ws/{room_id}?nickname={name}",
            "room_users": "/rooms/{room_id}/users",
            "room_history": "/rooms/{room_id}/history",
            "list_rooms": "/rooms"
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)