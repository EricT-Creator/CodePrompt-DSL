# Technical Design: FastAPI WebSocket Chat Server

## 1. WebSocket Connection Lifecycle

### Endpoint

`ws://host/ws/{room_id}?nickname={name}`

### Stages

1. **Accept**: FastAPI accepts the WebSocket. Extract `room_id` and `nickname`. Validate both are non-empty strings.
2. **Register**: Lazily create the room if needed. Insert WebSocket into `room.connections` set. Map connection to nickname in `room.nicknames`. Broadcast system message: `"<nickname> has joined"`.
3. **Loop**: `while True: text = await ws.receive_text()`. Build payload with sender, content, ISO timestamp. Broadcast. Store in history.
4. **Cleanup**: On `WebSocketDisconnect`, remove from set and nickname dict. Broadcast departure.

### Fault Tolerance

If `send_text` throws during broadcast, the failed connection is silently removed and iteration continues.

## 2. Room Management Data Structures

**Module-level registry**: `rooms: dict[str, Room] = {}`

**Room** fields:
- `connections: set[WebSocket]` — active sockets
- `nicknames: dict[WebSocket, str]` — display names
- `history: list[dict]` — message log, max 100

### REST Endpoints

- `GET /rooms/{room_id}/users` → `["alice", "bob", ...]`
- `GET /rooms/{room_id}/history` → array of message objects
- 404 if room does not exist

## 3. Broadcast Mechanism

No `asyncio.Queue` is used. On each incoming message:

1. Build JSON payload
2. Snapshot: `peers = list(room.connections)`
3. For each peer: `await peer.send_text(payload_str)` — catch and remove on failure
4. Append to `room.history`

Broadcasting is a direct iteration over the connection set. The snapshot prevents issues with set mutation during iteration.

## 4. Message History Storage

A plain `list[dict]` per room. After appending:
- If `len(room.history) > 100`, slice to keep last 100 entries

The capped list is returned directly by the history REST endpoint.

## 5. Constraint Acknowledgment

| # | Constraint | Design Response |
|---|-----------|----------------|
| 1 | Python + FastAPI | FastAPI server with WS + REST |
| 2 | No asyncio.Queue | Set-iteration broadcast |
| 3 | fastapi + uvicorn only | No other imports |
| 4 | Single file | One `.py` file |
| 5 | History capped at 100 | List with slicing |
| 6 | Code only | Pure code output |

## Constraint Checklist

1. [LANG] Write the complete server in Python using FastAPI as the web framework.
2. [NO_ASYNCQ] Do not use asyncio.Queue or any other async queue mechanism for message broadcasting.
3. [BROADCAST] Implement broadcasting by iterating over a set of active WebSocket connections and calling send_text on each.
4. [DEPS] Only use fastapi and uvicorn as external dependencies; import no other third-party packages.
5. [SINGLE_FILE] Place all server code, data structures, and route definitions in one Python file.
6. [HISTORY] Maintain message history as a list per room, capped at 100 entries by truncating after each append.
7. [CODE_ONLY] The final deliverable must be runnable code without any explanation or commentary text.
