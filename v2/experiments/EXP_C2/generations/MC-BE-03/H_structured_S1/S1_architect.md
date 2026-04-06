# Technical Design: FastAPI WebSocket Chat Server

## 1. WebSocket Connection Lifecycle

### Endpoint

`ws://host/ws/{room_id}?nickname={name}`

### Phases

1. **Accept**: FastAPI accepts the WebSocket upgrade. Extract `room_id` from path and `nickname` from query params. Validate both are non-empty.
2. **Register**: Add the WebSocket to the room's connection set and nickname mapping. Broadcast a "user joined" system message.
3. **Message Loop**: `while True: data = await websocket.receive_text()` — parse, broadcast to room, append to history.
4. **Disconnect**: Catch `WebSocketDisconnect`. Remove connection from room's set and nickname map. Broadcast "user left". If the room has zero connections, optionally clean up.

### Error Handling

Invalid params → send error JSON + close with 1008. Failed sends during broadcast → remove dead connection silently and continue.

## 2. Room Management Data Structures

### In-Memory Store

```
rooms: dict[str, Room] = {}
```

**Room** fields:
- `connections: set[WebSocket]` — live WebSocket objects
- `nicknames: dict[WebSocket, str]` — per-connection nickname
- `history: list[dict]` — capped message log

Rooms are created lazily when the first user connects to a given `room_id`.

### Endpoints

- `GET /rooms/{room_id}/users` → list of nicknames (from `room.nicknames.values()`)
- `GET /rooms/{room_id}/history` → JSON array of stored messages

## 3. Broadcast Mechanism

When user A sends a message in room R:

1. Build payload: `{"sender": nickname, "text": content, "timestamp": utcnow_iso}`
2. Snapshot the connection set: `targets = list(room.connections)`
3. For each `ws` in `targets`:
   - `await ws.send_text(json.dumps(payload))`
   - On exception: remove `ws` from `room.connections` and `room.nicknames`
4. Append payload to `room.history`; enforce cap

**No `asyncio.Queue`** is involved. Broadcasting is purely by iterating the set of active connections.

## 4. Message History Storage

Each room stores messages in a plain Python `list[dict]`. After every append:

```
if len(room.history) > 100:
    room.history = room.history[-100:]
```

This keeps the list at a maximum of 100 entries per room.

The `GET /rooms/{room_id}/history` endpoint returns this list directly.

## 5. Constraint Acknowledgment

| Constraint | Design Response |
|-----------|----------------|
| **[L]Python** | All code in Python |
| **[F]FastAPI** | FastAPI framework for HTTP + WebSocket |
| **[!D]NO_ASYNC_Q** | No asyncio.Queue anywhere; direct set iteration |
| **[BCAST]SET_ITER** | Broadcast loops over `room.connections` set |
| **[D]FASTAPI_ONLY** | Only fastapi + uvicorn dependencies |
| **[O]SINGLE_FILE** | Single .py file |
| **[HIST]LIST_100** | List per room, sliced to 100 max |
| **[OUT]CODE_ONLY** | Final output is code only |

## Constraint Checklist

1. [PYTHON] Write the entire server in Python.
2. [FASTAPI] Use FastAPI as the web framework with native WebSocket support.
3. [NO_ASYNCQ] Do not use asyncio.Queue or any async queue for message distribution.
4. [SET_BROADCAST] Broadcast messages by iterating over a set of active WebSocket connections.
5. [DEPS] Only import fastapi and uvicorn; no other third-party packages.
6. [SINGLE_FILE] Deliver everything in a single Python file.
7. [HISTORY] Store message history in a list per room, capped at 100 messages using slicing or truncation.
8. [CODE_ONLY] The final deliverable must be executable code with no surrounding explanation text.
