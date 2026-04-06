"""
WebSocket Chat Server for FastAPI - Set Iteration Broadcast

This module implements a WebSocket-based chat server with room management,
message history, and broadcast via direct set iteration (no asyncio.Queue).
"""

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Set, Dict, List, Optional, Tuple, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ============================================================================
# Data Models
# ============================================================================

@dataclass
class ChatMessage:
    """Represents a chat message."""
    type: str  # "message" or "system"
    nickname: str
    text: str
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type,
            "nickname": self.nickname,
            "text": self.text,
            "timestamp": self.timestamp
        }

class MessageRequest(BaseModel):
    """Request model for sending a message."""
    text: str = Field(..., min_length=1, max_length=1000, description="Message text")

class RoomInfoResponse(BaseModel):
    """Response model for room information."""
    room_id: str = Field(..., description="Room identifier")
    users: List[str] = Field(..., description="List of online users in the room")
    count: int = Field(..., description="Number of online users")

# ============================================================================
# Connection Manager
# ============================================================================

class ConnectionManager:
    """
    Manages WebSocket connections and room state.
    
    Uses direct set iteration for broadcasting (no asyncio.Queue per constraints).
    """
    
    def __init__(self):
        # room_id → set of (nickname, websocket) tuples
        self.rooms: Dict[str, Set[Tuple[str, WebSocket]]] = {}
        
        # room_id → list of last 100 messages
        self.history: Dict[str, List[ChatMessage]] = {}
        
        # Maximum history size per room
        self.MAX_HISTORY_SIZE = 100
    
    async def connect(self, room_id: str, nickname: str, websocket: WebSocket) -> None:
        """Accept a new connection and add to the room."""
        # Check nickname uniqueness within room
        if room_id in self.rooms:
            existing_nicknames = {nick for nick, _ in self.rooms[room_id]}
            if nickname in existing_nicknames:
                # Send close reason before closing
                await websocket.close(code=4001, reason="Nickname already taken")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nickname already taken in this room"
                )
        
        # Accept the connection
        await websocket.accept()
        
        # Initialize room if it doesn't exist
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
            self.history[room_id] = []
        
        # Add to room
        self.rooms[room_id].add((nickname, websocket))
    
    def disconnect(self, room_id: str, nickname: str) -> None:
        """Remove a connection from the room."""
        if room_id in self.rooms:
            # Find and remove the specific (nickname, websocket) tuple
            to_remove = None
            for nick, ws in self.rooms[room_id]:
                if nick == nickname:
                    to_remove = (nick, ws)
                    break
            
            if to_remove:
                self.rooms[room_id].discard(to_remove)
                
                # Clean up empty room
                if len(self.rooms[room_id]) == 0:
                    del self.rooms[room_id]
                    # Keep history for future connections
                    # del self.history[room_id]  # Optional: uncomment to clear history
    
    def get_history(self, room_id: str) -> List[Dict[str, Any]]:
        """Get message history for a room."""
        return [msg.to_dict() for msg in self.history.get(room_id, [])]
    
    def store_message(self, room_id: str, message: ChatMessage) -> None:
        """Store a message in the room's history."""
        if room_id not in self.history:
            self.history[room_id] = []
        
        history = self.history[room_id]
        history.append(message)
        
        # Keep only last MAX_HISTORY_SIZE messages
        if len(history) > self.MAX_HISTORY_SIZE:
            self.history[room_id] = history[-self.MAX_HISTORY_SIZE:]
    
    async def broadcast(self, room_id: str, message: ChatMessage) -> None:
        """
        Broadcast a message to all connections in a room.
        
        Uses direct set iteration per [BCAST]SET_ITER constraint.
        """
        if room_id not in self.rooms:
            return
        
        dead_connections: List[Tuple[str, WebSocket]] = []
        message_dict = message.to_dict()
        
        # Iterate over the set and send to each WebSocket
        for nickname, websocket in self.rooms[room_id]:
            try:
                await websocket.send_json(message_dict)
            except Exception:
                # Mark connection as dead for cleanup
                dead_connections.append((nickname, websocket))
        
        # Clean up dead connections (after iteration to avoid modifying set during iteration)
        for conn in dead_connections:
            self.rooms[room_id].discard(conn)
    
    def get_online_users(self, room_id: str) -> List[str]:
        """Get list of online users in a room."""
        if room_id not in self.rooms:
            return []
        
        # Extract nicknames from the set
        return [nickname for nickname, _ in self.rooms[room_id]]

# ============================================================================
# Helper Functions
# ============================================================================

def get_current_timestamp() -> str:
    """Get current ISO 8601 timestamp."""
    return datetime.utcnow().isoformat() + "Z"

def create_system_message(text: str) -> ChatMessage:
    """Create a system message."""
    return ChatMessage(
        type="system",
        nickname="system",
        text=text,
        timestamp=get_current_timestamp()
    )

def create_user_message(nickname: str, text: str) -> ChatMessage:
    """Create a user message."""
    return ChatMessage(
        type="message",
        nickname=nickname,
        text=text,
        timestamp=get_current_timestamp()
    )

# ============================================================================
# FastAPI Application Setup
# ============================================================================

app = FastAPI(
    title="WebSocket Chat Server",
    description="Real-time chat with room management and message history (capped at 100 messages)",
    version="1.0.0"
)

# Global connection manager instance
manager = ConnectionManager()

# ============================================================================
# API Endpoints
# ============================================================================

@app.websocket("/ws/{room_id}/{nickname}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, nickname: str):
    """
    WebSocket endpoint for chat connections.
    
    Flow:
    1. Validate nickname uniqueness
    2. Accept connection
    3. Send message history (up to 100 messages)
    4. Broadcast "user joined" system message
    5. Process incoming messages
    6. Clean up on disconnect
    """
    try:
        # Connect (includes nickname uniqueness check)
        await manager.connect(room_id, nickname, websocket)
        
        # Send history to the new user
        history = manager.get_history(room_id)
        for message_dict in history:
            try:
                await websocket.send_json(message_dict)
            except Exception:
                # If sending history fails, disconnect and exit
                manager.disconnect(room_id, nickname)
                return
        
        # Broadcast user joined system message
        join_message = create_system_message(f"{nickname} joined")
        manager.store_message(room_id, join_message)
        await manager.broadcast(room_id, join_message)
        
        # Message processing loop
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_json()
                
                # Validate message format
                if "text" not in data or not isinstance(data["text"], str):
                    continue
                
                text = data["text"].strip()
                if not text:
                    continue
                
                # Create and store user message
                user_message = create_user_message(nickname, text)
                manager.store_message(room_id, user_message)
                
                # Broadcast to all room members
                await manager.broadcast(room_id, user_message)
                
            except json.JSONDecodeError:
                # Ignore malformed JSON, keep connection alive
                continue
            except WebSocketDisconnect:
                # This will be caught by outer try-except
                raise
            except Exception:
                # Other exceptions, disconnect
                raise WebSocketDisconnect()
                
    except WebSocketDisconnect:
        # User disconnected
        manager.disconnect(room_id, nickname)
        
        # Broadcast user left system message
        leave_message = create_system_message(f"{nickname} left")
        manager.store_message(room_id, leave_message)
        await manager.broadcast(room_id, leave_message)
        
    except HTTPException:
        # Nickname uniqueness failure, already handled
        pass
    except Exception as e:
        # Unexpected error, clean up
        manager.disconnect(room_id, nickname)

@app.get("/rooms/{room_id}/users", response_model=RoomInfoResponse)
async def get_room_users(room_id: str):
    """
    Get online users in a room.
    
    This is a REST endpoint (not WebSocket) for querying room state.
    """
    users = manager.get_online_users(room_id)
    
    return RoomInfoResponse(
        room_id=room_id,
        users=users,
        count=len(users)
    )

@app.get("/rooms/{room_id}/history")
async def get_room_history(room_id: str):
    """
    Get message history for a room.
    
    Returns the last up to 100 messages stored in the room.
    """
    history = manager.get_history(room_id)
    
    return {
        "room_id": room_id,
        "history": history,
        "count": len(history)
    }

@app.post("/rooms/{room_id}/broadcast")
async def broadcast_message(room_id: str, message: MessageRequest):
    """
    Broadcast a system message to a room (admin endpoint).
    
    This endpoint allows sending system messages to a room
    without requiring a WebSocket connection.
    """
    if room_id not in manager.rooms:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    system_message = ChatMessage(
        type="system",
        nickname="admin",
        text=message.text,
        timestamp=get_current_timestamp()
    )
    
    manager.store_message(room_id, system_message)
    await manager.broadcast(room_id, system_message)
    
    return {"status": "broadcast_sent", "message": message.text}

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": get_current_timestamp(),
        "active_rooms": len(manager.rooms),
        "total_connections": sum(len(conn_set) for conn_set in manager.rooms.values())
    }

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)