# MC-BE-03: FastAPI WebSocket Chat Server - Technical Design Document

## 1. WebSocket Connection Lifecycle

### Connection States
```python
from enum import Enum
from dataclasses import dataclass
from fastapi import WebSocket

class ConnectionState(Enum):
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"

@dataclass
class Connection:
    websocket: WebSocket
    user_id: str
    nickname: str
    room_id: str
    state: ConnectionState
```

### Lifecycle Management
```python
class ConnectionManager:
    def __init__(self):
        # room_id -> set of Connection
        self._rooms: dict[str, set[Connection]] = {}
        # user_id -> Connection
        self._connections: dict[str, Connection] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str, nickname: str, room_id: str) -> Connection:
        """Handle new WebSocket connection."""
        await websocket.accept()
        
        conn = Connection(
            websocket=websocket,
            user_id=user_id,
            nickname=nickname,
            room_id=room_id,
            state=ConnectionState.CONNECTED
        )
        
        # Register connection
        self._connections[user_id] = conn
        if room_id not in self._rooms:
            self._rooms[room_id] = set()
        self._rooms[room_id].add(conn)
        
        return conn
    
    async def disconnect(self, user_id: str) -> None:
        """Handle WebSocket disconnection."""
        if user_id not in self._connections:
            return
        
        conn = self._connections[user_id]
        conn.state = ConnectionState.DISCONNECTING
        
        # Remove from room
        if conn.room_id in self._rooms:
            self._rooms[conn.room_id].discard(conn)
            if not self._rooms[conn.room_id]:
                del self._rooms[conn.room_id]
        
        # Remove from connections
        del self._connections[user_id]
        conn.state = ConnectionState.DISCONNECTED
    
    async def handle_connection(self, websocket: WebSocket, user_id: str, nickname: str, room_id: str):
        """Main connection handler with message loop."""
        conn = await self.connect(websocket, user_id, nickname, room_id)
        
        try:
            while conn.state == ConnectionState.CONNECTED:
                # Receive and process messages
                data = await websocket.receive_text()
                message = json.loads(data)
                await self.process_message(conn, message)
        except WebSocketDisconnect:
            pass
        finally:
            await self.disconnect(user_id)
            # Notify room of departure
            await self.broadcast_system_message(room_id, f"{nickname} left the room")
```

## 2. Room Management Data Structures

### Room Data Model
```python
from typing import TypedDict
from collections import deque

class Message(TypedDict):
    id: str
    user_id: str
    nickname: str
    content: str
    timestamp: str
    room_id: str

class Room:
    MAX_HISTORY = 100
    
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.connections: set[Connection] = set()
        # Deque with max length for automatic eviction
        self.message_history: deque[Message] = deque(maxlen=self.MAX_HISTORY)
        self.created_at = datetime.utcnow().isoformat()
    
    def add_message(self, message: Message) -> None:
        """Add message to history - automatically evicts oldest if >100."""
        self.message_history.append(message)
    
    def get_recent_messages(self, count: int = 50) -> list[Message]:
        """Get recent messages from history."""
        return list(self.message_history)[-count:]
    
    def get_online_users(self) -> list[dict]:
        """Get list of online users in room."""
        return [
            {"user_id": conn.user_id, "nickname": conn.nickname}
            for conn in self.connections
            if conn.state == ConnectionState.CONNECTED
        ]
```

### Room Registry
```python
class RoomRegistry:
    def __init__(self):
        self._rooms: dict[str, Room] = {}
    
    def get_or_create(self, room_id: str) -> Room:
        """Get existing room or create new one."""
        if room_id not in self._rooms:
            self._rooms[room_id] = Room(room_id)
        return self._rooms[room_id]
    
    def remove_if_empty(self, room_id: str) -> None:
        """Remove room if no connections remain."""
        if room_id in self._rooms and not self._rooms[room_id].connections:
            del self._rooms[room_id]
```

## 3. Broadcast Mechanism

### Set Iteration Broadcast
```python
import asyncio
from typing import Any

class ConnectionManager:
    # ... previous implementation ...
    
    async def broadcast_to_room(
        self,
        room_id: str,
        message: dict[str, Any],
        exclude_user: str | None = None
    ) -> None:
        """Broadcast message to all connections in room using set iteration."""
        if room_id not in self._rooms:
            return
        
        message_json = json.dumps(message)
        
        # Iterate over set directly - no asyncio.Queue
        disconnected = []
        for conn in self._rooms[room_id]:
            if exclude_user and conn.user_id == exclude_user:
                continue
            
            try:
                await conn.websocket.send_text(message_json)
            except WebSocketDisconnect:
                disconnected.append(conn.user_id)
            except Exception:
                # Handle other errors, mark for cleanup
                disconnected.append(conn.user_id)
        
        # Cleanup disconnected clients
        for user_id in disconnected:
            await self.disconnect(user_id)
    
    async def broadcast_system_message(self, room_id: str, content: str) -> None:
        """Broadcast system message to room."""
        message = {
            "type": "system",
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_room(room_id, message)
    
    async def broadcast_chat_message(
        self,
        room_id: str,
        user_id: str,
        nickname: str,
        content: str
    ) -> Message:
        """Broadcast user chat message to room."""
        message: Message = {
            "id": generate_message_id(),
            "user_id": user_id,
            "nickname": nickname,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "room_id": room_id
        }
        
        # Store in room history
        if room_id in self._rooms:
            self._rooms[room_id].add_message(message)
        
        # Broadcast to all room members
        await self.broadcast_to_room(room_id, {
            "type": "message",
            "data": message
        })
        
        return message
```

### Concurrent Send Handling
```python
async def broadcast_with_gather(self, room_id: str, message: dict) -> None:
    """Alternative: Use asyncio.gather for concurrent sends."""
    if room_id not in self._rooms:
        return
    
    message_json = json.dumps(message)
    
    # Create send tasks for all connections
    tasks = [
        self._send_safe(conn, message_json)
        for conn in self._rooms[room_id]
    ]
    
    # Execute all sends concurrently
    await asyncio.gather(*tasks, return_exceptions=True)

async def _send_safe(self, conn: Connection, message: str) -> None:
    """Safely send message, handling disconnections."""
    try:
        await conn.websocket.send_text(message)
    except Exception:
        await self.disconnect(conn.user_id)
```

## 4. Message History Storage

### In-Memory Storage with Size Limit
```python
from collections import deque

class MessageStore:
    def __init__(self, max_per_room: int = 100):
        self._store: dict[str, deque[Message]] = {}
        self._max_per_room = max_per_room
    
    def add(self, room_id: str, message: Message) -> None:
        """Add message to room history."""
        if room_id not in self._store:
            # Use deque with maxlen for automatic eviction
            self._store[room_id] = deque(maxlen=self._max_per_room)
        self._store[room_id].append(message)
    
    def get_history(self, room_id: str, limit: int = 100) -> list[Message]:
        """Get message history for room."""
        if room_id not in self._store:
            return []
        messages = list(self._store[room_id])
        return messages[-limit:] if limit < len(messages) else messages
    
    def clear_room(self, room_id: str) -> None:
        """Clear history for a specific room."""
        if room_id in self._store:
            del self._store[room_id]
```

### History API Endpoint
```python
@app.get("/rooms/{room_id}/history")
async def get_room_history(room_id: str, limit: int = 50) -> list[Message]:
    """Get message history for a room."""
    return message_store.get_history(room_id, limit)

@app.get("/rooms/{room_id}/users")
async def get_room_users(room_id: str) -> list[dict]:
    """Get online users in a room."""
    if room_id not in room_registry._rooms:
        return []
    return room_registry._rooms[room_id].get_online_users()
```

## 5. Constraint Acknowledgment

### Python + FastAPI
**Addressed by:** Application built with FastAPI framework. WebSocket endpoints use FastAPI's WebSocket class.

### No asyncio.Queue for broadcast, use set iteration
**Addressed by:** Broadcast implemented by iterating over `set[Connection]` directly. No `asyncio.Queue` used for message distribution. Each connection receives message via direct `websocket.send_text()` call.

### fastapi + uvicorn only
**Addressed by:** Only dependencies are FastAPI and uvicorn. No additional WebSocket or chat libraries.

### Single file
**Addressed by:** All chat server code in single Python file. Connection manager, room logic, and endpoints co-located.

### In-memory list, max 100 msgs per room
**Addressed by:** Message history stored using `collections.deque(maxlen=100)`. Automatic eviction of oldest messages when limit reached.

### Code only
**Addressed by:** Output contains only Python code. No markdown in generated file.
