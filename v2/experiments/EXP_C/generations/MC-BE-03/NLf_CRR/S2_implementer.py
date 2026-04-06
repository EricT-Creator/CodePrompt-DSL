"""WebSocket Chat Server with multi-room support, broadcasting, nicknames, and capped history."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Dict, List, Literal, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

# ─── Models ───────────────────────────────────────────────────────────────────

class Message(BaseModel):
    id: str
    room_id: str
    sender_nickname: str
    content: str
    timestamp: str
    type: Literal["chat", "system", "join", "leave"]


class MessageResponse(BaseModel):
    id: str
    sender: str
    content: str
    timestamp: str
    type: str


class RoomInfo(BaseModel):
    room_id: str
    user_count: int
    users: List[str]


# ─── Connection Manager ──────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, dict] = {}

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        self.active_connections[connection_id] = websocket
        self.connection_metadata[connection_id] = {
            "nickname": None,
            "room": None,
            "joined_at": None,
        }
        return connection_id

    def disconnect(self, connection_id: str) -> Optional[dict]:
        metadata = self.connection_metadata.get(connection_id)
        self.active_connections.pop(connection_id, None)
        self.connection_metadata.pop(connection_id, None)
        return metadata

    def get_websocket(self, connection_id: str) -> Optional[WebSocket]:
        return self.active_connections.get(connection_id)

    def set_metadata(self, connection_id: str, key: str, value: object) -> None:
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id][key] = value

    def get_metadata(self, connection_id: str) -> Optional[dict]:
        return self.connection_metadata.get(connection_id)


# ─── Room Manager ─────────────────────────────────────────────────────────────

class RoomManager:
    MAX_HISTORY = 100

    def __init__(self) -> None:
        self.rooms: Dict[str, Set[str]] = {}
        self.message_history: Dict[str, List[Message]] = {}
        self.room_nicknames: Dict[str, Dict[str, str]] = {}  # room -> {connection_id: nickname}

    def create_room(self, room_id: str) -> None:
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
            self.message_history[room_id] = []
            self.room_nicknames[room_id] = {}

    def join_room(self, room_id: str, connection_id: str, nickname: str) -> None:
        self.create_room(room_id)
        self.rooms[room_id].add(connection_id)
        self.room_nicknames[room_id][connection_id] = nickname

    def leave_room(self, room_id: str, connection_id: str) -> Optional[str]:
        if room_id not in self.rooms:
            return None
        self.rooms[room_id].discard(connection_id)
        nickname = self.room_nicknames.get(room_id, {}).pop(connection_id, None)
        if not self.rooms[room_id]:
            del self.rooms[room_id]
            del self.message_history[room_id]
            del self.room_nicknames[room_id]
        return nickname

    def get_room_connections(self, room_id: str) -> Set[str]:
        return self.rooms.get(room_id, set()).copy()

    def get_online_users(self, room_id: str) -> List[str]:
        nicks = self.room_nicknames.get(room_id, {})
        return list(nicks.values())

    def store_message(self, room_id: str, message: Message) -> None:
        if room_id not in self.message_history:
            return
        history = self.message_history[room_id]
        history.append(message)
        if len(history) > self.MAX_HISTORY:
            self.message_history[room_id] = history[-self.MAX_HISTORY:]

    def get_history(self, room_id: str) -> List[Message]:
        return self.message_history.get(room_id, [])

    def update_nickname(self, room_id: str, connection_id: str, new_nickname: str) -> None:
        if room_id in self.room_nicknames and connection_id in self.room_nicknames[room_id]:
            self.room_nicknames[room_id][connection_id] = new_nickname

    def list_rooms(self) -> List[RoomInfo]:
        result = []
        for room_id, connections in self.rooms.items():
            result.append(
                RoomInfo(
                    room_id=room_id,
                    user_count=len(connections),
                    users=self.get_online_users(room_id),
                )
            )
        return result


# ─── Globals ──────────────────────────────────────────────────────────────────

connection_manager = ConnectionManager()
room_manager = RoomManager()

app = FastAPI(title="WebSocket Chat Server")


# ─── Broadcasting (iterate connection set) ────────────────────────────────────

async def broadcast_to_room(
    room_id: str,
    message: dict,
    exclude_connection: Optional[str] = None,
) -> None:
    connection_ids = room_manager.get_room_connections(room_id)
    for cid in connection_ids:
        if cid == exclude_connection:
            continue
        ws = connection_manager.get_websocket(cid)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                pass


async def send_to(connection_id: str, message: dict) -> None:
    ws = connection_manager.get_websocket(connection_id)
    if ws:
        try:
            await ws.send_json(message)
        except Exception:
            pass


# ─── WebSocket Handlers ──────────────────────────────────────────────────────

async def handle_join(connection_id: str, data: dict) -> None:
    room_id = data.get("room_id", "general")
    nickname = data.get("nickname", f"user-{connection_id[:6]}")

    # Leave current room if any
    meta = connection_manager.get_metadata(connection_id)
    if meta and meta.get("room"):
        old_room = meta["room"]
        old_nick = room_manager.leave_room(old_room, connection_id)
        if old_nick:
            leave_msg = {
                "type": "system",
                "content": f"{old_nick} left the room",
                "timestamp": datetime.utcnow().isoformat(),
            }
            await broadcast_to_room(old_room, leave_msg)
            await broadcast_to_room(old_room, {"type": "user_list", "users": room_manager.get_online_users(old_room)})

    # Join new room
    room_manager.join_room(room_id, connection_id, nickname)
    connection_manager.set_metadata(connection_id, "room", room_id)
    connection_manager.set_metadata(connection_id, "nickname", nickname)
    connection_manager.set_metadata(connection_id, "joined_at", datetime.utcnow().isoformat())

    # Store system message
    join_message = Message(
        id=str(uuid.uuid4()),
        room_id=room_id,
        sender_nickname="system",
        content=f"{nickname} joined the room",
        timestamp=datetime.utcnow().isoformat(),
        type="join",
    )
    room_manager.store_message(room_id, join_message)

    # Broadcast join
    await broadcast_to_room(
        room_id,
        {"type": "system", "content": f"{nickname} joined the room", "timestamp": join_message.timestamp},
        exclude_connection=connection_id,
    )

    # Send history to joiner
    history = room_manager.get_history(room_id)
    history_data = [
        {"type": m.type, "sender": m.sender_nickname, "content": m.content, "timestamp": m.timestamp}
        for m in history[-50:]  # Last 50 for initial load
    ]
    await send_to(connection_id, {"type": "history", "messages": history_data})

    # Broadcast user list
    await broadcast_to_room(room_id, {"type": "user_list", "users": room_manager.get_online_users(room_id)})

    # Confirm join to sender
    await send_to(connection_id, {"type": "joined", "room_id": room_id, "nickname": nickname})


async def handle_message(connection_id: str, data: dict) -> None:
    meta = connection_manager.get_metadata(connection_id)
    if not meta or not meta.get("room"):
        await send_to(connection_id, {"type": "error", "content": "You must join a room first"})
        return

    room_id = meta["room"]
    nickname = meta.get("nickname", "anonymous")
    content = data.get("content", "")

    if not content.strip():
        return

    msg = Message(
        id=str(uuid.uuid4()),
        room_id=room_id,
        sender_nickname=nickname,
        content=content,
        timestamp=datetime.utcnow().isoformat(),
        type="chat",
    )
    room_manager.store_message(room_id, msg)

    await broadcast_to_room(
        room_id,
        {
            "type": "chat",
            "sender": nickname,
            "content": content,
            "timestamp": msg.timestamp,
            "id": msg.id,
        },
    )


async def handle_leave(connection_id: str) -> None:
    meta = connection_manager.get_metadata(connection_id)
    if not meta or not meta.get("room"):
        return

    room_id = meta["room"]
    nickname = room_manager.leave_room(room_id, connection_id)
    connection_manager.set_metadata(connection_id, "room", None)

    if nickname and room_id in room_manager.rooms:
        leave_msg = Message(
            id=str(uuid.uuid4()),
            room_id=room_id,
            sender_nickname="system",
            content=f"{nickname} left the room",
            timestamp=datetime.utcnow().isoformat(),
            type="leave",
        )
        room_manager.store_message(room_id, leave_msg)
        await broadcast_to_room(
            room_id,
            {"type": "system", "content": f"{nickname} left the room", "timestamp": leave_msg.timestamp},
        )
        await broadcast_to_room(room_id, {"type": "user_list", "users": room_manager.get_online_users(room_id)})


async def handle_set_nickname(connection_id: str, data: dict) -> None:
    new_nickname = data.get("nickname", "").strip()
    if not new_nickname:
        await send_to(connection_id, {"type": "error", "content": "Nickname cannot be empty"})
        return

    meta = connection_manager.get_metadata(connection_id)
    old_nickname = meta.get("nickname", "anonymous") if meta else "anonymous"
    connection_manager.set_metadata(connection_id, "nickname", new_nickname)

    if meta and meta.get("room"):
        room_id = meta["room"]
        room_manager.update_nickname(room_id, connection_id, new_nickname)
        await broadcast_to_room(
            room_id,
            {
                "type": "system",
                "content": f"{old_nickname} changed their name to {new_nickname}",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
        await broadcast_to_room(room_id, {"type": "user_list", "users": room_manager.get_online_users(room_id)})


# ─── WebSocket Endpoint ──────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    connection_id = await connection_manager.connect(websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await send_to(connection_id, {"type": "error", "content": "Invalid JSON"})
                continue

            action = data.get("action")

            if action == "join":
                await handle_join(connection_id, data)
            elif action == "message":
                await handle_message(connection_id, data)
            elif action == "leave":
                await handle_leave(connection_id)
            elif action == "set_nickname":
                await handle_set_nickname(connection_id, data)
            else:
                await send_to(connection_id, {"type": "error", "content": f"Unknown action: {action}"})

    except WebSocketDisconnect:
        meta = connection_manager.disconnect(connection_id)
        if meta and meta.get("room"):
            room_id = meta["room"]
            nickname = room_manager.leave_room(room_id, connection_id)
            if nickname and room_id in room_manager.rooms:
                leave_msg = Message(
                    id=str(uuid.uuid4()),
                    room_id=room_id,
                    sender_nickname="system",
                    content=f"{nickname} disconnected",
                    timestamp=datetime.utcnow().isoformat(),
                    type="leave",
                )
                room_manager.store_message(room_id, leave_msg)
                await broadcast_to_room(
                    room_id,
                    {"type": "system", "content": f"{nickname} disconnected", "timestamp": leave_msg.timestamp},
                )
                await broadcast_to_room(
                    room_id,
                    {"type": "user_list", "users": room_manager.get_online_users(room_id)},
                )


# ─── REST Endpoints ───────────────────────────────────────────────────────────

@app.get("/rooms")
async def list_rooms() -> List[RoomInfo]:
    return room_manager.list_rooms()


@app.get("/rooms/{room_id}/history")
async def get_room_history(room_id: str) -> List[MessageResponse]:
    history = room_manager.get_history(room_id)
    return [
        MessageResponse(
            id=msg.id,
            sender=msg.sender_nickname,
            content=msg.content,
            timestamp=msg.timestamp,
            type=msg.type,
        )
        for msg in history
    ]


@app.get("/rooms/{room_id}/users")
async def get_online_users(room_id: str) -> List[str]:
    return room_manager.get_online_users(room_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
