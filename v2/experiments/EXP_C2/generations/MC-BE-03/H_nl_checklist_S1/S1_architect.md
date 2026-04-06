# Technical Design: FastAPI WebSocket Chat Server

## 1. WebSocket Connection Lifecycle

### Connection Endpoint

`ws://host/ws/{room_id}?nickname={name}`

### Lifecycle Stages

1. **Upgrade & Validate**: Accept WebSocket. Extract `room_id` from path, `nickname` from query string. If either is missing, send error frame and close (code 1008).
2. **Join Room**: Lazily create room if it doesn't exist. Add connection to room's `connections` set, map it in `nicknames`. Broadcast a system message: `"<nickname> joined"`.
3. **Receive Loop**: Continuously `await websocket.receive_text()`. For each message, build a timestamped JSON payload, broadcast it, and store it in history.
4. **Disconnect**: On `WebSocketDisconnect`, remove from `connections` and `nicknames`. Broadcast `"<nickname> left"`.

### Error Resilience

During broadcast, if a `send_text` call fails, catch the exception, remove the dead connection, and continue with remaining connections.

## 2. Room Management Data Structures

### Module-Level Registry

```
rooms: dict[str, Room] = {}
```

**Room** (plain class or dataclass):
- `connections: set[WebSocket]` — currently active WebSocket instances
- `nicknames: dict[WebSocket, str]` — maps each connection to its display name
- `history: list[dict]` — most recent messages, capped at 100

### REST Endpoints

- `GET /rooms/{room_id}/users` → JSON list of nicknames
- `GET /rooms/{room_id}/history` → JSON array of message objects

Both return 404 if the room does not exist.

## 3. Broadcast Mechanism

### Set-Iteration Approach

On message receipt:

1. Construct payload: `{"sender": nick, "text": msg, "timestamp": utcnow_str}`
2. Take a snapshot: `peers = list(room.connections)`
3. For each `peer` in `peers`:
   - `await peer.send_text(json.dumps(payload))`
   - On failure → remove `peer` from room state
4. Append payload to `room.history`, enforce cap

No `asyncio.Queue` is used. The broadcast is a straightforward loop over the connection set.

## 4. Message History Storage

A plain `list[dict]` per room. After each append:

- If length exceeds 100, truncate: `room.history = room.history[-100:]`

This guarantees at most 100 messages retained per room. The history is served directly via the REST endpoint.

## 5. Constraint Acknowledgment

| Constraint | Design Response |
|-----------|----------------|
| **[L]Python** | All server code in Python |
| **[F]FastAPI** | FastAPI for HTTP routes + WebSocket handling |
| **[!D]NO_ASYNC_Q** | No asyncio.Queue used |
| **[BCAST]SET_ITER** | Broadcast by iterating connection set |
| **[D]FASTAPI_ONLY** | Only fastapi and uvicorn |
| **[O]SINGLE_FILE** | Single .py file |
| **[HIST]LIST_100** | List capped at 100 per room |
| **[OUT]CODE_ONLY** | Deliverable is code only |

## Constraint Checklist

1. The entire server must be written in Python, using only Python standard library features alongside the explicitly permitted packages.
2. FastAPI must be the sole web framework, handling both HTTP REST endpoints and WebSocket connections.
3. The application must not use asyncio.Queue or any other asynchronous queue mechanism for distributing messages to connected clients.
4. Message broadcasting must be performed by iterating over a set of active WebSocket connections and sending to each one individually.
5. The only third-party packages allowed are fastapi and uvicorn; no other external dependencies may be imported.
6. All server logic, routes, data structures, and helper functions must reside in a single Python file.
7. Each room's message history must be stored in a Python list that is truncated to retain no more than 100 messages.
8. The final output must consist exclusively of executable Python code, with no surrounding explanation, commentary, or documentation text.
