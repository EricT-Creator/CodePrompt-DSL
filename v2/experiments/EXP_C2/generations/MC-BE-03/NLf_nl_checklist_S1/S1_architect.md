# Technical Design: FastAPI WebSocket Chat Server

## 1. WebSocket Connection Lifecycle

### Endpoint

`ws://host/ws/{room_id}?nickname={name}`

### Lifecycle

1. **Upgrade**: Server accepts the WebSocket handshake. Parse `room_id` from URL path and `nickname` from query parameters. Reject if nickname is missing.
2. **Join**: Create room on first access. Add socket to room's connection set and record nickname. Broadcast a join notification.
3. **Message Loop**: Continuously receive text frames. For each:
   - Construct a JSON message with sender, text, and ISO-8601 timestamp
   - Iterate over the room's connection set and send to each peer
   - Append to the room's capped history list
4. **Leave**: On disconnect, remove the socket from the set and nickname map. Broadcast a leave notification.

### Resilience

Failed `send_text` calls during broadcast are caught. The broken connection is removed from the room and iteration continues uninterrupted.

## 2. Room Management Data Structures

### Storage

Module-level dictionary: `rooms: dict[str, Room] = {}`

**Room** attributes:
- `connections: set[WebSocket]` — live connections
- `nicknames: dict[WebSocket, str]` — socket-to-name mapping
- `history: list[dict]` — message objects, max 100

Rooms are lazily instantiated.

### Endpoints

- `GET /rooms/{room_id}/users` → list of nicknames
- `GET /rooms/{room_id}/history` → list of message objects
- Returns 404 for nonexistent rooms

## 3. Broadcast Mechanism

No `asyncio.Queue` is used. Broadcasting works by iterating directly over the connection set:

1. Snapshot the set: `targets = list(room.connections)`
2. For each target: `await target.send_text(json.dumps(payload))`
3. On failure: silently remove the dead connection
4. Store the message in history after broadcast

This is the simplest possible fan-out, with no intermediate buffering.

## 4. Message History Storage

A plain Python list stores message dictionaries. After each append, enforce the cap:

- If length exceeds 100, truncate to the last 100 entries via slicing

The capped list is served as-is through the history endpoint.

## 5. Constraint Acknowledgment

| # | Constraint | Design Response |
|---|-----------|----------------|
| 1 | Python + FastAPI | FastAPI handles both WebSocket and REST |
| 2 | No asyncio.Queue | Direct set-iteration broadcast |
| 3 | fastapi + uvicorn only | No other external packages |
| 4 | Single Python file | All code in one file |
| 5 | History capped at 100 | List with slicing after append |
| 6 | Code only output | Deliverable is pure code |

## Constraint Checklist

1. The server must be implemented entirely in Python, using the FastAPI framework for all HTTP and WebSocket handling.
2. Broadcasting messages to room participants must not use asyncio.Queue or any asynchronous queue; instead, messages must be sent by looping over a set of active WebSocket connections.
3. The only permitted third-party packages are fastapi and uvicorn, and no other external libraries may be imported or used.
4. Every piece of server logic, including routes, data models, and helper functions, must be contained in a single Python file.
5. Message history for each room must be stored in a Python list that never exceeds 100 entries, enforced by truncation after every append.
6. The final deliverable must be pure executable Python code without any explanatory prose, comments beyond standard docstrings, or documentation text surrounding it.
