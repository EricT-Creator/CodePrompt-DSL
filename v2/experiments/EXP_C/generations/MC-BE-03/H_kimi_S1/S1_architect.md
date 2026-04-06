# MC-BE-03: WebSocket Chat Server — Technical Design Document

**Model**: Kimi-K2.5  
**Stage**: S1 Architect  
**Encoding**: Header (H)  
**Date**: 2026-04-01

---

## 1. WebSocket Connection Lifecycle

### 1.1 Connection States

```
Connecting -> Connected -> Authenticated -> In Room -> Disconnected
```

### 1.2 Lifecycle Events

| Event | Trigger | Action |
|-------|---------|--------|
| `connect` | Client opens WS | Accept connection, create connection state |
| `join_room` | Client sends join message | Add to room, broadcast join notification |
| `message` | Client sends chat | Store in history, broadcast to room |
| `disconnect` | Client closes | Remove from room, broadcast leave notification |

### 1.3 FastAPI WebSocket Handler

```python
@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()
    
    # Wait for nickname
    data = await websocket.receive_json()
    nickname = data.get("nickname", "Anonymous")
    
    # Register connection
    await join_room(room_id, websocket, nickname)
    
    try:
        while True:
            data = await websocket.receive_json()
            await handle_message(room_id, websocket, data)
    except WebSocketDisconnect:
        await leave_room(room_id, websocket)
```

---

## 2. Room Management Data Structures

### 2.1 In-Memory Storage

```python
from fastapi import WebSocket
from collections import defaultdict

# Room -> Set of connections
room_connections: dict[str, set[WebSocket]] = defaultdict(set)

# Connection -> Metadata
connection_info: dict[WebSocket, dict] = {}

# Room -> Message history (capped at 100)
room_history: dict[str, list[dict]] = defaultdict(list)
```

### 2.2 Room Operations

```python
async def join_room(room_id: str, websocket: WebSocket, nickname: str):
    """Add connection to room"""
    room_connections[room_id].add(websocket)
    connection_info[websocket] = {"nickname": nickname, "room": room_id}
    
    # Send recent history
    history = room_history.get(room_id, [])
    await websocket.send_json({
        "type": "history",
        "messages": history
    })
    
    # Broadcast join
    await broadcast(room_id, {
        "type": "system",
        "message": f"{nickname} joined the room"
    }, exclude=websocket)

async def leave_room(room_id: str, websocket: WebSocket):
    """Remove connection from room"""
    room_connections[room_id].discard(websocket)
    info = connection_info.pop(websocket, {})
    
    # Broadcast leave
    await broadcast(room_id, {
        "type": "system",
        "message": f"{info.get('nickname', 'Someone')} left the room"
    })
```

---

## 3. Broadcast Mechanism

### 3.1 Set Iteration Broadcast

```python
async def broadcast(room_id: str, message: dict, exclude: WebSocket = None):
    """Broadcast message to all connections in room"""
    connections = room_connections.get(room_id, set())
    
    for conn in connections:
        if conn != exclude:
            try:
                await conn.send_json(message)
            except Exception:
                # Handle disconnected clients
                pass
```

### 3.2 Message Types

```python
{
    "type": "chat",
    "nickname": "user123",
    "message": "Hello!",
    "timestamp": "2026-04-01T10:00:00Z"
}

{
    "type": "system",
    "message": "user123 joined the room"
}

{
    "type": "history",
    "messages": [...]
}
```

---

## 4. Message History Storage

### 4.1 Capped List Implementation

```python
MAX_HISTORY = 100

def add_to_history(room_id: str, message: dict):
    """Add message to room history, maintaining cap"""
    history = room_history[room_id]
    history.append(message)
    
    # Trim to max size
    if len(history) > MAX_HISTORY:
        room_history[room_id] = history[-MAX_HISTORY:]
```

### 4.2 History Retrieval

```python
@app.get("/rooms/{room_id}/history")
async def get_history(room_id: str):
    """HTTP endpoint for fetching message history"""
    return {
        "room_id": room_id,
        "messages": room_history.get(room_id, [])
    }
```

---

## 5. Constraint Acknowledgment

| Constraint | How Design Addresses It |
|------------|------------------------|
| `[L]Python` | Python 3.10+ implementation |
| `[F]FastAPI` | FastAPI WebSocket support |
| `[!D]NO_ASYNC_Q` | No asyncio.Queue; direct set iteration |
| `[BCAST]SET_ITER` | Broadcast via iterating connection set |
| `[D]FASTAPI_ONLY` | Only FastAPI dependency |
| `[O]SINGLE_FILE` | All code in single file |
| `[HIST]LIST_100` | Capped list at 100 messages per room |
| `[OUT]CODE_ONLY` | Output will be code only |

---

## 6. API Summary

| Endpoint | Type | Description |
|----------|------|-------------|
| `GET /rooms/{room_id}/users` | HTTP | List online users |
| `GET /rooms/{room_id}/history` | HTTP | Get message history |
| `/ws/{room_id}` | WebSocket | Chat connection |

---

## 7. File Structure

```
MC-BE-03/
├── H_kimi_S1/
│   └── S1_architect.md (this file)
└── S2_developer/
    └── main.py
```

---

*Document generated for EXP-C Phase 1 — Header encoding condition*
