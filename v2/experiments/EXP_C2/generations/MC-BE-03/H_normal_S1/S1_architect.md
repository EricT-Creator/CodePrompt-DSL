# Technical Design: FastAPI WebSocket Chat Server

## 1. WebSocket Connection Lifecycle

### Connection Flow

1. **Connect**: Client opens `ws://host/ws/{room_id}?nickname={name}`. The server upgrades to WebSocket, validates parameters, registers the connection in the room's active set.
2. **Active**: Server reads messages in a loop (`while True: await websocket.receive_text()`). Each message is broadcast to all peers in the same room.
3. **Disconnect**: On `WebSocketDisconnect` exception, the server removes the connection from the room's set and broadcasts a "user left" notification.

### Error Handling

- If the nickname is empty or the room_id is malformed, the server sends a JSON error frame and closes the connection with code 1008.
- Any unexpected exception in the message loop triggers cleanup (removal from set) and graceful close.

## 2. Room Management Data Structures

### Module-Level State

A `dict[str, Room]` maps room ids to `Room` objects.

**Room** (dataclass or plain class):
- `connections: set[WebSocket]` — active WebSocket instances
- `nicknames: dict[WebSocket, str]` — mapping from connection to nickname
- `history: list[dict]` — message history (capped at 100)

Rooms are created lazily on first join. When the last user leaves, the room object can remain (preserving history) or be garbage-collected (design choice; preserving is simpler).

### User Tracking

Each connection carries its nickname. The `nicknames` dict enables:
- Broadcast attribution (who sent what)
- The online user list endpoint

## 3. Broadcast Mechanism

### Iteration-Based Broadcast

When a message arrives from user A in room R:

1. Construct a JSON payload: `{"sender": nickname, "text": message, "timestamp": iso_now}`
2. Iterate over `room.connections` (a `set`):
   - For each connection, call `await connection.send_text(json.dumps(payload))`
   - If sending fails (broken pipe), catch the exception, remove that connection from the set, and continue
3. Append the payload to `room.history`

**No `asyncio.Queue`** is used. The broadcast is a direct iteration over the set of active connections.

### Concurrency Consideration

Since FastAPI's WebSocket handling is async-per-connection, multiple messages could arrive nearly simultaneously. The `set` iteration is safe because Python's GIL prevents concurrent mutation during iteration in CPython's event loop, and each `await send_text` yields cooperatively. For robustness, iterate over a snapshot (`list(room.connections)`) to avoid set-changed-during-iteration if a disconnect handler fires between sends.

## 4. Message History Storage

### Capped List

Each room maintains a `list[dict]` for message history. After appending a new message:

- If `len(room.history) > 100`, slice to keep only the last 100: `room.history = room.history[-100:]`

Alternatively, use `collections.deque(maxlen=100)` — but a plain list with slicing is equally valid and avoids import.

### History Endpoint

A REST endpoint `GET /rooms/{room_id}/history` returns the stored list as JSON. If the room doesn't exist, return 404.

### Online Users Endpoint

`GET /rooms/{room_id}/users` returns `[nickname for nickname in room.nicknames.values()]` as a JSON array.

## 5. Constraint Acknowledgment

| Constraint | How Addressed |
|-----------|---------------|
| **[L]Python** | Entire server in Python |
| **[F]FastAPI** | FastAPI app with WebSocket routes and REST endpoints |
| **[!D]NO_ASYNC_Q** | No `asyncio.Queue`; broadcast via set iteration |
| **[BCAST]SET_ITER** | Broadcast iterates `room.connections` set directly |
| **[D]FASTAPI_ONLY** | Only `fastapi` and `uvicorn` in dependencies; no other third-party packages |
| **[O]SINGLE_FILE** | Everything in one Python file |
| **[HIST]LIST_100** | Message history stored as a list capped at 100 per room |
| **[OUT]CODE_ONLY** | Final deliverable is code only, no explanation text |
