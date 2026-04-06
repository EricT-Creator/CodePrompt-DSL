# Technical Design Document: WebSocket Chat Server

**Task**: MC-BE-03  
**Encoding**: Header (H)  
**Stage**: S1 Architect  
**Header**: `[L]Python [F]FastAPI [!D]NO_ASYNC_Q [BCAST]SET_ITER [D]FASTAPI_ONLY [O]SINGLE_FILE [HIST]LIST_100 [OUT]CODE_ONLY`

---

## 1. WebSocket Connection Lifecycle

### Connection Flow

```
Client                          Server
  |                               |
  |--- WS /ws/{room}/{nick} ---->|  1. Validate room & nickname
  |                               |  2. Add connection to room set
  |                               |  3. Broadcast "user joined"
  |                               |  4. Send last N history messages
  |<---- history messages --------|
  |                               |
  |--- { "text": "hello" } ----->|  5. Receive message
  |                               |  6. Store in room history
  |<---- broadcast to room -------|  7. Broadcast to all room members
  |                               |
  |--- connection close -------->|  8. Remove from room set
  |                               |  9. Broadcast "user left"
```

### Connection Handling

```python
@app.websocket("/ws/{room_id}/{nickname}")
async def websocket_endpoint(ws: WebSocket, room_id: str, nickname: str):
    await ws.accept()
    manager.connect(room_id, nickname, ws)
    try:
        # Send history
        for msg in manager.get_history(room_id):
            await ws.send_json(msg)
        # Broadcast join
        await manager.broadcast(room_id, system_msg(f"{nickname} joined"))
        # Message loop
        while True:
            data = await ws.receive_json()
            message = build_message(nickname, data["text"])
            manager.store_message(room_id, message)
            await manager.broadcast(room_id, message)
    except WebSocketDisconnect:
        manager.disconnect(room_id, nickname)
        await manager.broadcast(room_id, system_msg(f"{nickname} left"))
```

### Error Handling

- `WebSocketDisconnect` exception triggers cleanup.
- Malformed JSON from client is caught and ignored (connection stays open).
- If `ws.send_json()` fails for a specific client during broadcast, that client is silently removed from the room set.

---

## 2. Room Management Data Structures

### Core Manager Class

```python
class ConnectionManager:
    rooms: dict[str, set[tuple[str, WebSocket]]]
    # room_id → set of (nickname, websocket) pairs

    history: dict[str, list[dict]]
    # room_id → list of message dicts, capped at 100
```

### Room Lifecycle

- **Room creation**: Implicit — first connection to a `room_id` creates the entry in `rooms` and `history`.
- **Room destruction**: Optional — when the last user leaves, the room entry can be cleaned up or left for future reconnections.

### User Tracking

Each connection is stored as a `(nickname, WebSocket)` tuple in the room's set. This allows:
- **Online user list**: Extract all nicknames from the set.
- **Targeted send**: Iterate the set to broadcast.
- **Disconnect cleanup**: Remove the specific tuple by identity.

### Nickname Uniqueness

Within a room, nicknames should be unique. On connect, check if the nickname already exists in the room set. If so, reject the connection with a close code 4001 and reason "Nickname already taken."

---

## 3. Broadcast Mechanism

### Set Iteration Approach

Per the `[BCAST]SET_ITER` constraint, broadcast is implemented by iterating over the room's connection set:

```python
async def broadcast(self, room_id: str, message: dict) -> None:
    if room_id not in self.rooms:
        return
    dead_connections = []
    for nickname, ws in self.rooms[room_id]:
        try:
            await ws.send_json(message)
        except Exception:
            dead_connections.append((nickname, ws))
    # Clean up dead connections
    for conn in dead_connections:
        self.rooms[room_id].discard(conn)
```

### Key Design Points

- **No asyncio.Queue for broadcast**: The constraint `[!D]NO_ASYNC_Q` prohibits using `asyncio.Queue` for message distribution. Instead, direct iteration over the connection set is used.
- **Dead connection cleanup**: If `send_json` raises, the connection is marked for removal. Removal happens after iteration to avoid modifying the set during iteration.
- **Message format**: All messages are JSON dicts with `{ "type": "message"|"system", "nickname": str, "text": str, "timestamp": str }`.

---

## 4. Message History Storage

### Capped List Implementation

```python
class RoomHistory:
    _store: dict[str, list[dict]]  # room_id → message list
    MAX_SIZE: int = 100

    def add(self, room_id: str, message: dict) -> None:
        if room_id not in self._store:
            self._store[room_id] = []
        history = self._store[room_id]
        history.append(message)
        if len(history) > self.MAX_SIZE:
            # Trim from the front (oldest messages)
            self._store[room_id] = history[-self.MAX_SIZE:]
```

### History Delivery

When a new client connects:
1. Retrieve the room's history list (up to 100 messages).
2. Send each message individually via `ws.send_json()`.
3. Then broadcast the "user joined" system message.

This ensures the new user sees past context before live messages begin flowing.

### Message Structure

```python
{
    "type": "message",        # or "system"
    "nickname": "alice",      # or "system" for system messages
    "text": "Hello everyone!",
    "timestamp": "2026-04-01T12:00:00Z"
}
```

### Online User List Endpoint

A REST endpoint (not WebSocket) for querying online users:

```
GET /rooms/{room_id}/users → { "room_id": str, "users": list[str], "count": int }
```

---

## 5. Constraint Acknowledgment

| Constraint | Header Token | How Addressed |
|-----------|-------------|---------------|
| Language: Python | `[L]Python` | Entire implementation in Python 3.10+. |
| Framework: FastAPI | `[F]FastAPI` | WebSocket endpoint and REST endpoints defined via FastAPI. |
| No asyncio.Queue | `[!D]NO_ASYNC_Q` | Broadcast does not use `asyncio.Queue`. Messages are sent by direct set iteration. |
| Broadcast via set iteration | `[BCAST]SET_ITER` | `ConnectionManager.broadcast()` iterates `rooms[room_id]` set and calls `ws.send_json()` on each. |
| FastAPI only | `[D]FASTAPI_ONLY` | No external packages beyond FastAPI (and its bundled dependencies like Starlette/uvicorn). |
| Single file | `[O]SINGLE_FILE` | All classes, endpoints, and logic in one `.py` file. |
| History: list capped at 100 | `[HIST]LIST_100` | `list[dict]` per room, trimmed to keep only the last 100 entries on each append. |
| Code only output | `[OUT]CODE_ONLY` | Final S2 deliverable will be pure code. |
