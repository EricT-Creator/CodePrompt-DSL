"""
MC-BE-03: WebSocket Chat Server
[L]Python [F]FastAPI [!D]NO_ASYNC_Q [BCAST]SET_ITER [D]FASTAPI_ONLY [O]SINGLE_FILE [HIST]LIST_100 [OUT]CODE_ONLY
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel


# ─── Configuration ────────────────────────────────────────────────────────────

MAX_HISTORY = 100

# ─── In-Memory Storage ────────────────────────────────────────────────────────

room_connections: dict[str, set[WebSocket]] = defaultdict(set)
connection_info: dict[int, dict[str, str]] = {}  # id(ws) -> metadata
room_history: dict[str, list[dict]] = defaultdict(list)

# ─── Response Models ──────────────────────────────────────────────────────────

class RoomUsersResponse(BaseModel):
    room_id: str
    users: list[str]
    count: int


class RoomHistoryResponse(BaseModel):
    room_id: str
    messages: list[dict]
    count: int


# ─── Broadcast via set iteration ──────────────────────────────────────────────

async def broadcast(room_id: str, message: dict, exclude: WebSocket | None = None) -> None:
    connections = room_connections.get(room_id, set())
    disconnected: list[WebSocket] = []

    for conn in connections:
        if conn is exclude:
            continue
        try:
            await conn.send_json(message)
        except Exception:
            disconnected.append(conn)

    # Clean up disconnected clients
    for conn in disconnected:
        connections.discard(conn)
        ws_id = id(conn)
        if ws_id in connection_info:
            del connection_info[ws_id]


# ─── History Management ──────────────────────────────────────────────────────

def add_to_history(room_id: str, message: dict) -> None:
    history = room_history[room_id]
    history.append(message)
    if len(history) > MAX_HISTORY:
        room_history[room_id] = history[-MAX_HISTORY:]


# ─── Room Operations ─────────────────────────────────────────────────────────

async def join_room(room_id: str, websocket: WebSocket, nickname: str) -> None:
    room_connections[room_id].add(websocket)
    connection_info[id(websocket)] = {"nickname": nickname, "room": room_id}

    # Send recent history
    history = room_history.get(room_id, [])
    await websocket.send_json({
        "type": "history",
        "messages": history,
    })

    # Send user list
    users = [
        info["nickname"]
        for ws in room_connections[room_id]
        for ws_id in [id(ws)]
        if ws_id in connection_info
        for info in [connection_info[ws_id]]
    ]
    await websocket.send_json({
        "type": "user_list",
        "users": users,
    })

    # Broadcast join notification
    system_msg = {
        "type": "system",
        "message": f"{nickname} joined the room",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    add_to_history(room_id, system_msg)
    await broadcast(room_id, system_msg, exclude=websocket)


async def leave_room(room_id: str, websocket: WebSocket) -> None:
    room_connections[room_id].discard(websocket)
    ws_id = id(websocket)
    info = connection_info.pop(ws_id, {})
    nickname = info.get("nickname", "Someone")

    system_msg = {
        "type": "system",
        "message": f"{nickname} left the room",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    add_to_history(room_id, system_msg)
    await broadcast(room_id, system_msg)

    # Clean up empty rooms
    if not room_connections[room_id]:
        del room_connections[room_id]


async def handle_message(room_id: str, websocket: WebSocket, data: dict) -> None:
    ws_id = id(websocket)
    info = connection_info.get(ws_id, {})
    nickname = info.get("nickname", "Anonymous")

    msg_type = data.get("type", "chat")

    if msg_type == "chat":
        chat_msg = {
            "type": "chat",
            "nickname": nickname,
            "message": data.get("message", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        add_to_history(room_id, chat_msg)
        await broadcast(room_id, chat_msg)
    elif msg_type == "typing":
        await broadcast(
            room_id,
            {"type": "typing", "nickname": nickname},
            exclude=websocket,
        )


# ─── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(title="WebSocket Chat Server")


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str) -> None:
    await websocket.accept()

    # Wait for initial join message with nickname
    try:
        data = await websocket.receive_json()
        nickname = data.get("nickname", "Anonymous")
    except Exception:
        await websocket.close(code=1008, reason="Expected join message")
        return

    await join_room(room_id, websocket, nickname)

    try:
        while True:
            data = await websocket.receive_json()
            await handle_message(room_id, websocket, data)
    except WebSocketDisconnect:
        await leave_room(room_id, websocket)
    except Exception:
        await leave_room(room_id, websocket)


@app.get("/rooms/{room_id}/users", response_model=RoomUsersResponse)
async def get_room_users(room_id: str) -> RoomUsersResponse:
    connections = room_connections.get(room_id, set())
    users: list[str] = []
    for ws in connections:
        ws_id = id(ws)
        info = connection_info.get(ws_id)
        if info:
            users.append(info["nickname"])

    return RoomUsersResponse(
        room_id=room_id,
        users=users,
        count=len(users),
    )


@app.get("/rooms/{room_id}/history", response_model=RoomHistoryResponse)
async def get_history(room_id: str) -> RoomHistoryResponse:
    messages = room_history.get(room_id, [])
    return RoomHistoryResponse(
        room_id=room_id,
        messages=messages,
        count=len(messages),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
