# Technical Design Document — WebSocket Chat Server

## 1. Overview

A FastAPI WebSocket chat server supporting multiple chat rooms, real-time message broadcast, user nicknames, an online user list endpoint, and in-memory message history capped at 100 messages per room.

## 2. WebSocket Connection Lifecycle

### Connection Establishment
1. Client connects to `ws://host/ws/{room_id}?nickname={name}`.
2. Server extracts `room_id` from the path and `nickname` from query params.
3. Server calls `await websocket.accept()`.
4. Server registers the connection in the room's connection set.
5. Server broadcasts a "user joined" system message to the room.
6. Server sends the recent message history to the newly connected client.

### Active Session
- Server enters an infinite `await websocket.receive_text()` loop.
- Each received message is wrapped in a `ChatMessage` envelope (nickname, timestamp, content).
- The message is appended to the room's history buffer.
- The message is broadcast to all other connections in the same room via set iteration.

### Disconnection
- When `receive_text()` raises `WebSocketDisconnect`, the server removes the connection from the room's set.
- A "user left" system message is broadcast to remaining members.
- If the room's connection set is empty, the room data structure may optionally be retained (for history) or cleaned up after a timeout.

## 3. Room Management Data Structures

### Core Structures

- **RoomManager**: a singleton class holding all room state.
  - `rooms: dict[str, Room]`
  - Methods: `join(room_id, ws, nickname)`, `leave(room_id, ws)`, `broadcast(room_id, message)`, `get_users(room_id)`, `get_history(room_id)`

- **Room**: `{ connections: dict[WebSocket, str], history: deque[ChatMessage] }`
  - `connections`: maps each WebSocket object to its nickname string. Using a dict (rather than a set) allows nickname lookup by connection.
  - `history`: a `collections.deque(maxlen=100)` — automatically evicts oldest messages when the cap is reached.

- **ChatMessage**: `{ nickname: str, content: str, timestamp: str, msg_type: "user" | "system" }`

### Room Creation
- Rooms are created lazily on first join. No explicit "create room" endpoint.

## 4. Broadcast Mechanism

### Set Iteration Approach (No asyncio.Queue)

When a message arrives from one client:
1. Iterate over `room.connections.keys()` (the set of WebSocket objects).
2. For each connection that is *not* the sender, call `await ws.send_text(json_message)`.
3. If `send_text` raises a `ConnectionClosed` or `RuntimeError`, catch the exception, remove that connection from the set, and continue iterating.

### Why Not asyncio.Queue
- Per the constraint, broadcast uses direct set iteration rather than a per-client `asyncio.Queue` consumer pattern.
- Trade-off: simpler code but the broadcast loop is sequential. For this scale (in-memory, single-process), this is acceptable.

### System Messages
- "User joined" and "user left" events are broadcast as `ChatMessage` with `msg_type = "system"`.

## 5. Message History Storage

### Capped Deque
- Each room holds a `collections.deque(maxlen=100)`.
- When a new message is appended and the deque is at capacity, the oldest message is automatically discarded.
- This satisfies the "100 messages per room" cap with zero manual eviction logic.

### History Delivery
- On new connection, the server sends the full deque contents as a JSON array to the joining client, enabling them to see recent context.

## 6. REST Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/rooms/{room_id}/users` | Returns list of nicknames currently connected to the room |
| `GET` | `/rooms/{room_id}/history` | Returns the message history (up to 100) for the room |
| `GET` | `/rooms` | Lists all active room IDs |
| `WebSocket` | `/ws/{room_id}?nickname={name}` | WebSocket connection endpoint |

### Online User List
- The `/rooms/{room_id}/users` endpoint iterates `room.connections.values()` and returns the nickname list.
- This is a REST endpoint (not WebSocket), allowing non-WS clients to query room membership.

## 7. Constraint Acknowledgment

| # | Constraint | Design Response |
|---|-----------|----------------|
| 1 | **Python + FastAPI** | FastAPI app with WebSocket route and REST endpoints. |
| 2 | **No asyncio.Queue for broadcast, use set iteration** | Broadcast iterates over the room's `connections` dict directly and calls `send_text` on each. No Queue, no pub/sub. |
| 3 | **fastapi + uvicorn only** | Only `fastapi` and `uvicorn` as non-stdlib dependencies. `collections.deque` and `json` are stdlib. |
| 4 | **Single file** | All logic — RoomManager, data classes, endpoints, WebSocket handler — in one `.py` file. |
| 5 | **In-memory list, max 100 msgs per room** | `collections.deque(maxlen=100)` per room. Purely in-memory, no database or file persistence. |
| 6 | **Code only** | Deliverable is pure Python source code. |
