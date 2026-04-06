# MC-BE-03: WebSocket Chat Server - Technical Design

## Overview

This document outlines the technical design for a FastAPI WebSocket chat server with multi-room support, broadcasting, user nicknames, and capped message history.

## 1. WebSocket Connection Lifecycle

### Connection States

```
┌─────────┐    connect()     ┌──────────┐
│  IDLE   │ ────────────────►│ CONNECTED│
└─────────┘                  └────┬─────┘
                                  │ join_room()
                                  ▼
                            ┌──────────┐
                            │ IN_ROOM  │◄──────┐
                            └────┬─────┘       │
                                 │ leave_room() │
                                 └──────────────┘
                                  │ disconnect()
                                  ▼
                            ┌──────────┐
                            │ CLOSED   │
                            └──────────┘
```

### Lifecycle Implementation

```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}  # connection_id -> websocket
        self.connection_metadata: Dict[str, dict] = {}      # connection_id -> {nickname, room, joined_at}
    
    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        connection_id = str(uuid4())
        self.active_connections[connection_id] = websocket
        return connection_id
    
    def disconnect(self, connection_id: str) -> None:
        # Remove from room if in one
        metadata = self.connection_metadata.get(connection_id)
        if metadata and metadata.get("room"):
            room_manager.leave_room(metadata["room"], connection_id)
        
        # Clean up
        self.active_connections.pop(connection_id, None)
        self.connection_metadata.pop(connection_id, None)
```

### WebSocket Handler

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    connection_id = await connection_manager.connect(websocket)
    
    try:
        while True:
            # Receive and parse message
            data = await websocket.receive_text()
            message = json.loads(data)
            
            action = message.get("action")
            
            if action == "join":
                await handle_join(connection_id, message)
            elif action == "message":
                await handle_message(connection_id, message)
            elif action == "leave":
                await handle_leave(connection_id)
            elif action == "set_nickname":
                await handle_set_nickname(connection_id, message)
    except WebSocketDisconnect:
        connection_manager.disconnect(connection_id)
```

## 2. Room Management Data Structures

### Room Registry

```python
class RoomManager:
    def __init__(self):
        # room_id -> set of connection_ids
        self.rooms: Dict[str, Set[str]] = {}
        # room_id -> list of messages (capped at 100)
        self.message_history: Dict[str, List[Message]] = {}
        # room_id -> set of nicknames
        self.room_nicknames: Dict[str, Set[str]] = {}
    
    def create_room(self, room_id: str) -> None:
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
            self.message_history[room_id] = []
            self.room_nicknames[room_id] = set()
    
    def join_room(self, room_id: str, connection_id: str, nickname: str) -> bool:
        self.create_room(room_id)
        self.rooms[room_id].add(connection_id)
        self.room_nicknames[room_id].add(nickname)
        return True
    
    def leave_room(self, room_id: str, connection_id: str) -> None:
        if room_id in self.rooms:
            self.rooms[room_id].discard(connection_id)
            # Clean up empty rooms
            if not self.rooms[room_id]:
                del self.rooms[room_id]
                del self.message_history[room_id]
                del self.room_nicknames[room_id]
    
    def get_room_connections(self, room_id: str) -> Set[str]:
        return self.rooms.get(room_id, set())
    
    def get_online_users(self, room_id: str) -> List[str]:
        return list(self.room_nicknames.get(room_id, []))
```

### Message Model

```python
class Message(BaseModel):
    id: str
    room_id: str
    sender_nickname: str
    content: str
    timestamp: datetime
    type: Literal["chat", "system", "join", "leave"]
```

## 3. Broadcast Mechanism

### Iteration-Based Broadcasting

```python
async def broadcast_to_room(
    room_id: str,
    message: dict,
    exclude_connection: Optional[str] = None
) -> None:
    """Broadcast message to all connections in a room by iterating connection set."""
    connection_ids = room_manager.get_room_connections(room_id)
    
    for connection_id in connection_ids:
        if connection_id == exclude_connection:
            continue
        
        websocket = connection_manager.active_connections.get(connection_id)
        if websocket:
            try:
                await websocket.send_json(message)
            except Exception:
                # Handle disconnected clients gracefully
                pass
```

### Message Flow

```
User sends message:
  ├─ Parse message JSON
  ├─ Validate user is in a room
  ├─ Create Message object with timestamp
  ├─ Store in room history (with cap)
  ├─ Broadcast to all room connections
  │   └─ Iterate room connection set
  │       └─ Send to each WebSocket
  └─ Confirm to sender
```

### History Management

```python
def store_message(room_id: str, message: Message) -> None:
    """Store message with 100 message cap per room."""
    history = room_manager.message_history[room_id]
    history.append(message)
    
    # Cap at 100 messages (FIFO)
    if len(history) > 100:
        room_manager.message_history[room_id] = history[-100:]
```

## 4. Message History Storage

### History Retrieval

```python
@app.get("/rooms/{room_id}/history")
async def get_room_history(room_id: str) -> List[MessageResponse]:
    """Get message history for a room (last 100 messages)."""
    history = room_manager.message_history.get(room_id, [])
    return [
        MessageResponse(
            id=msg.id,
            sender=msg.sender_nickname,
            content=msg.content,
            timestamp=msg.timestamp,
            type=msg.type
        )
        for msg in history
    ]

@app.get("/rooms/{room_id}/users")
async def get_online_users(room_id: str) -> List[str]:
    """Get list of online users in a room."""
    return room_manager.get_online_users(room_id)
```

### WebSocket Protocol

```python
# Client -> Server messages
{
    "action": "join",
    "room_id": "general",
    "nickname": "Alice"
}

{
    "action": "message",
    "content": "Hello everyone!"
}

{
    "action": "set_nickname",
    "nickname": "Alice2"
}

# Server -> Client messages
{
    "type": "system",
    "content": "Alice joined the room"
}

{
    "type": "chat",
    "sender": "Alice",
    "content": "Hello everyone!",
    "timestamp": "2024-01-15T10:30:00Z"
}

{
    "type": "user_list",
    "users": ["Alice", "Bob", "Charlie"]
}
```

## 5. Constraint Acknowledgment

| Constraint | Design Response |
|------------|-----------------|
| **Python + FastAPI** | Use FastAPI with native WebSocket support |
| **No async queue for broadcast** | Iterate `Set[str]` of connection IDs directly; no asyncio.Queue for message distribution |
| **FastAPI + uvicorn only** | No additional third-party packages |
| **Single Python file** | All code (models, room manager, WebSocket handler, endpoints) in one file |
| **Capped at 100 messages** | `store_message()` enforces FIFO cap at 100 per room |
| **Output code only** | Design structured for direct implementation |

## Summary

This design implements a multi-room WebSocket chat server using FastAPI's native WebSocket support. Broadcasting is achieved by iterating a set of active connections rather than using message queues. Each room maintains capped message history (FIFO at 100 messages) and tracks online users. The connection lifecycle manages join/leave events and cleanup, while the WebSocket protocol supports nicknames, room switching, and real-time messaging.
