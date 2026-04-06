# Technical Design Document — WebSocket Chat Server

## 1. Overview

This document describes the architecture for a FastAPI WebSocket chat server with multi-room support. The server broadcasts messages to all users in the same room, supports user nicknames, provides an online user list endpoint, and maintains in-memory message history capped at 100 messages per room.

## 2. WebSocket Connection Lifecycle

### 2.1 Connection Flow

1. **Connect**: Client opens a WebSocket to `/ws/{room_id}?nickname={name}`.
2. **Handshake**: Server accepts the connection, registers the client in the room's active connections set, and broadcasts a "user joined" system message.
3. **Message Loop**: Server enters an infinite receive loop. On each incoming message, it parses the content, stores it in room history, and broadcasts to all connections in the room.
4. **Disconnect**: On `WebSocketDisconnect` exception, the server removes the client from the room's connection set, broadcasts a "user left" system message, and cleans up empty rooms.

### 2.2 Error Handling

- If the WebSocket disconnects unexpectedly, the `except WebSocketDisconnect` handler ensures cleanup.
- Malformed messages (non-JSON or missing fields) are silently dropped or responded to with an error frame.

## 3. Room Management Data Structures

### 3.1 Core Structures

- **rooms**: `dict[str, set[WebSocket]]` — Maps room IDs to sets of active WebSocket connections.
- **user_info**: `dict[WebSocket, UserInfo]` — Maps each WebSocket connection to its user metadata.
- **message_history**: `dict[str, list[Message]]` — Maps room IDs to their message history lists.

### 3.2 Interfaces

- **UserInfo**: `{ nickname: str; room_id: str; connected_at: str }`
- **Message**: `{ id: str; room_id: str; nickname: str; content: str; timestamp: str; type: "user" | "system" }`
- **RoomInfo**: `{ room_id: str; online_count: int; users: list[str] }`

### 3.3 Room Lifecycle

- **Room creation**: Implicit. When the first user connects to a `room_id`, the room entry is created in all three dictionaries.
- **Room deletion**: When the last user disconnects, the room entry is removed to prevent memory leaks.

## 4. Broadcast Mechanism

### 4.1 Approach

Broadcasting is performed by iterating the set of active connections for the target room. For each connection in `rooms[room_id]`, send the message JSON via `websocket.send_json()`.

### 4.2 Failure Handling

During iteration, if `send_json()` raises an exception for a specific connection (indicating it's stale or broken), that connection is marked for removal. After the iteration completes, stale connections are removed from the room set. This prevents a broken connection from blocking delivery to other users.

### 4.3 Implementation Pattern

```
async def broadcast(room_id: str, message: Message):
    stale = set()
    for ws in rooms.get(room_id, set()):
        try:
            await ws.send_json(message.to_dict())
        except Exception:
            stale.add(ws)
    for ws in stale:
        rooms[room_id].discard(ws)
        user_info.pop(ws, None)
```

Note: No asyncio.Queue is used for broadcasting. Direct iteration over the connection set is the mandated approach.

## 5. Message History Storage

### 5.1 Storage Model

Each room maintains a `list[Message]` in the `message_history` dictionary.

### 5.2 Capping at 100 Messages

When a new message is appended and the list exceeds 100 entries, the oldest message is removed. This is implemented as:

```
history.append(new_message)
if len(history) > 100:
    history.pop(0)
```

Alternatively, `collections.deque(maxlen=100)` could be used, but since only standard containers and no additional imports are required beyond what's available, a plain list with manual capping is straightforward.

### 5.3 History Retrieval

A REST endpoint (GET `/rooms/{room_id}/history`) returns the message history list for a given room. This allows new users to see recent messages upon joining.

## 6. API Endpoints

### 6.1 WebSocket

| Path | Description |
|------|-------------|
| `WS /ws/{room_id}?nickname={name}` | Join a room and start chatting |

### 6.2 REST

| Method | Path | Description |
|--------|------|-------------|
| GET | `/rooms` | List all active rooms with user counts |
| GET | `/rooms/{room_id}/users` | List online users (nicknames) in a room |
| GET | `/rooms/{room_id}/history` | Retrieve message history for a room |

## 7. Message Protocol

### 7.1 Client → Server

```json
{ "content": "Hello everyone!" }
```

### 7.2 Server → Client

```json
{
  "id": "msg-uuid",
  "room_id": "general",
  "nickname": "Alice",
  "content": "Hello everyone!",
  "timestamp": "2026-04-01T12:00:00Z",
  "type": "user"
}
```

System messages (join/leave) use `type: "system"` and `nickname: "system"`.

## 8. Constraint Acknowledgment

| # | Constraint | How the Design Addresses It |
|---|-----------|---------------------------|
| 1 | Python with FastAPI | The server is built on FastAPI with native WebSocket support and Pydantic models for REST endpoints. |
| 2 | No asyncio.Queue for broadcasting; iterate active connections | Broadcasting explicitly iterates `rooms[room_id]` (a set of WebSocket objects). No queue is used for message distribution. |
| 3 | Only fastapi and uvicorn, no other third-party packages | All data structures are Python builtins (dict, set, list). UUID generation uses `uuid` from stdlib. No additional packages. |
| 4 | Single Python file | All WebSocket handlers, REST endpoints, data structures, and broadcast logic are in one `.py` file. |
| 5 | Message history capped at 100 per room | Each room's `message_history` list enforces a max length of 100 by removing the oldest entry when the cap is exceeded. |
| 6 | Output code only, no explanation text | The final implementation will be pure code. This document is the design artifact. |
