# Technical Design: FastAPI WebSocket Chat Server

## 1. WebSocket Connection Lifecycle

### Endpoint Design

The WebSocket endpoint is mounted at `/ws/{room_id}` with the nickname passed as a query parameter.

### Connection Phases

1. **Accept & Validate**: The server accepts the WebSocket upgrade. It extracts `room_id` from the URL path and `nickname` from the query string. If `nickname` is missing, it sends an error payload and closes the connection.

2. **Room Registration**: If the room doesn't exist yet, create it. Add the WebSocket instance to the room's active connection set and record the nickname mapping. Broadcast a system message announcing the new user.

3. **Message Processing Loop**: Enter `while True: msg = await websocket.receive_text()`. For each received message:
   - Build a JSON payload with sender, text, and timestamp
   - Broadcast to all connections in the room by iterating over the connection set
   - Append to the room's history list

4. **Disconnection**: On `WebSocketDisconnect`, remove the connection from the room's set and nickname mapping. Broadcast a departure notice.

### Error Handling

If `send_text` fails for a particular connection during broadcast, catch the exception, remove that dead connection, and continue sending to the rest. This prevents one broken client from disrupting others.

## 2. Room Management Data Structures

### Module-Level Store

A dictionary at module level maps room identifiers to room objects:

**Room** (class or dataclass):
- `connections: set` — a set of active WebSocket instances
- `nicknames: dict` — maps each WebSocket to its user's nickname string
- `history: list` — a list of message dictionaries, capped at 100

Rooms are created on-demand (lazy initialization) when the first user connects to a given room_id.

### REST Endpoints

- `GET /rooms/{room_id}/users` — returns the list of nicknames currently connected to the room
- `GET /rooms/{room_id}/history` — returns the stored message history as a JSON array

Both return HTTP 404 if the room doesn't exist.

## 3. Broadcast Mechanism

### Direct Set Iteration

Broadcasting does not use `asyncio.Queue` or any async queue. Instead:

1. Create a snapshot of the connection set: `targets = list(room.connections)`
2. For each `ws` in `targets`:
   - Call `await ws.send_text(payload_json)`
   - On exception: remove `ws` from `room.connections` and `room.nicknames`
3. After broadcast, append the message to `room.history`

The snapshot prevents "set changed size during iteration" issues if a disconnect occurs mid-broadcast.

### Why No asyncio.Queue

The constraint explicitly forbids async queues. The set-iteration approach is simpler: each incoming message triggers a synchronous fan-out to all peers. Since FastAPI handles each WebSocket connection as a separate async task, the broadcast `await`s are cooperative and non-blocking.

## 4. Message History Storage

### Capped List Approach

Each room has a `history: list[dict]`. After appending a new message:

```
if len(room.history) > 100:
    room.history = room.history[-100:]
```

This ensures at most 100 messages per room. Old messages beyond the cap are discarded.

The history is accessible via `GET /rooms/{room_id}/history`, which returns the entire list as JSON.

## 5. Constraint Acknowledgment

| # | Constraint | Design Response |
|---|-----------|----------------|
| 1 | Python with FastAPI | Single FastAPI application with WebSocket + REST routes |
| 2 | No asyncio.Queue | Broadcast by iterating connection set, not via queue |
| 3 | FastAPI and uvicorn only | No other third-party packages imported |
| 4 | Single Python file | All logic in one `.py` file |
| 5 | History list capped at 100 | Plain list with post-append truncation |
| 6 | Code only output | Final deliverable is pure code |
