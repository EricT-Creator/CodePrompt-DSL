"""
MC-BE-03: WebSocket Chat Server
Engineering Constraints: Python + FastAPI. No asyncio.Queue for broadcast, use set iteration.
fastapi + uvicorn only. Single file. In-memory list, max 100 msgs per room. Code only.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# ── Data Models ─────────────────────────────────────────────────────────


@dataclass
class ChatMessage:
    message_id: str
    room_id: str
    sender_id: str
    sender_nickname: str
    content: str
    message_type: str = "text"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "room_id": self.room_id,
            "sender_id": self.sender_id,
            "sender_nickname": self.sender_nickname,
            "content": self.content,
            "message_type": self.message_type,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class ConnectionState:
    connection_id: str
    websocket: WebSocket
    user_id: Optional[str] = None
    nickname: Optional[str] = None
    rooms: Set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    is_alive: bool = True

    def update_activity(self) -> None:
        self.last_activity = datetime.utcnow()


@dataclass
class ChatRoom:
    room_id: str
    name: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    max_messages: int = 100
    connections: Set[str] = field(default_factory=set)
    messages: List[ChatMessage] = field(default_factory=list)
    is_public: bool = True

    def add_message(self, message: ChatMessage) -> None:
        self.messages.append(message)
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

    def get_recent_messages(self, count: int = 20) -> List[Dict[str, Any]]:
        recent = self.messages[-count:] if self.messages else []
        return [m.to_dict() for m in recent]


# ── Connection Manager ──────────────────────────────────────────────────


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: Dict[str, ConnectionState] = {}

    def add(self, conn: ConnectionState) -> None:
        self.connections[conn.connection_id] = conn

    def remove(self, connection_id: str) -> Optional[ConnectionState]:
        return self.connections.pop(connection_id, None)

    def get(self, connection_id: str) -> Optional[ConnectionState]:
        return self.connections.get(connection_id)

    @property
    def count(self) -> int:
        return len(self.connections)


# ── Room Manager ────────────────────────────────────────────────────────


class RoomManager:
    def __init__(self) -> None:
        self.rooms: Dict[str, ChatRoom] = {}
        # Create default room
        self.create_room("general", "General Chat")
        self.create_room("random", "Random")

    def create_room(self, room_id: str, name: str, is_public: bool = True) -> ChatRoom:
        if room_id in self.rooms:
            return self.rooms[room_id]
        room = ChatRoom(room_id=room_id, name=name, is_public=is_public)
        self.rooms[room_id] = room
        return room

    def get_room(self, room_id: str) -> Optional[ChatRoom]:
        return self.rooms.get(room_id)

    def list_public_rooms(self) -> List[Dict[str, Any]]:
        return [
            {
                "room_id": r.room_id,
                "name": r.name,
                "online_count": len(r.connections),
                "is_public": r.is_public,
            }
            for r in self.rooms.values()
            if r.is_public
        ]

    async def broadcast_to_room(
        self,
        room_id: str,
        message_data: Dict[str, Any],
        conn_manager: ConnectionManager,
        exclude_id: Optional[str] = None,
    ) -> None:
        room = self.get_room(room_id)
        if not room:
            return

        # Use set iteration for broadcast (no asyncio.Queue)
        targets = room.connections.copy()
        dead_connections: List[str] = []

        for cid in targets:
            if cid == exclude_id:
                continue
            conn = conn_manager.get(cid)
            if conn and conn.is_alive:
                try:
                    await conn.websocket.send_json(message_data)
                except Exception:
                    dead_connections.append(cid)
            else:
                dead_connections.append(cid)

        # Cleanup dead connections
        for cid in dead_connections:
            room.connections.discard(cid)


# ── Globals ─────────────────────────────────────────────────────────────

conn_manager = ConnectionManager()
room_manager = RoomManager()

# ── Heartbeat ───────────────────────────────────────────────────────────

_heartbeat_task: Optional[asyncio.Task[None]] = None


async def heartbeat_loop() -> None:
    while True:
        await asyncio.sleep(30)
        now = datetime.utcnow()
        dead: List[str] = []
        for cid, conn in conn_manager.connections.items():
            inactive = (now - conn.last_activity).total_seconds()
            if inactive > 120:
                dead.append(cid)

        for cid in dead:
            conn = conn_manager.remove(cid)
            if conn:
                conn.is_alive = False
                for rid in conn.rooms:
                    room = room_manager.get_room(rid)
                    if room:
                        room.connections.discard(cid)
                try:
                    await conn.websocket.close()
                except Exception:
                    pass


# ── Message Handler ─────────────────────────────────────────────────────


async def handle_ws_message(connection_id: str, raw: str) -> None:
    conn = conn_manager.get(connection_id)
    if not conn:
        return

    conn.update_activity()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        await conn.websocket.send_json({"type": "error", "message": "Invalid JSON"})
        return

    msg_type = data.get("type", "")

    if msg_type == "chat_message":
        room_id = data.get("room_id", "general")
        content = data.get("content", "").strip()
        if not content:
            return

        room = room_manager.get_room(room_id)
        if not room or connection_id not in room.connections:
            await conn.websocket.send_json({"type": "error", "message": "Not in room"})
            return

        message = ChatMessage(
            message_id=str(uuid.uuid4()),
            room_id=room_id,
            sender_id=connection_id,
            sender_nickname=conn.nickname or "Anonymous",
            content=content,
            metadata=data.get("metadata", {}),
        )
        room.add_message(message)

        broadcast_data = {"type": "chat_message", **message.to_dict()}
        await room_manager.broadcast_to_room(room_id, broadcast_data, conn_manager, exclude_id=connection_id)

        # Acknowledge to sender
        await conn.websocket.send_json({"type": "message_ack", "message_id": message.message_id})

    elif msg_type == "join_room":
        room_id = data.get("room_id", "general")
        room = room_manager.get_room(room_id)
        if not room:
            room = room_manager.create_room(room_id, room_id)

        conn.rooms.add(room_id)
        room.connections.add(connection_id)

        # Send history
        history = room.get_recent_messages(20)
        await conn.websocket.send_json({"type": "room_joined", "room_id": room_id, "history": history, "online_count": len(room.connections)})

        # Broadcast join
        await room_manager.broadcast_to_room(
            room_id,
            {"type": "user_joined", "room_id": room_id, "nickname": conn.nickname or "Anonymous", "online_count": len(room.connections)},
            conn_manager,
            exclude_id=connection_id,
        )

    elif msg_type == "leave_room":
        room_id = data.get("room_id", "general")
        conn.rooms.discard(room_id)
        room = room_manager.get_room(room_id)
        if room:
            room.connections.discard(connection_id)
            await room_manager.broadcast_to_room(
                room_id,
                {"type": "user_left", "room_id": room_id, "nickname": conn.nickname or "Anonymous", "online_count": len(room.connections)},
                conn_manager,
            )

    elif msg_type == "set_nickname":
        nickname = data.get("nickname", "").strip()
        if nickname:
            conn.nickname = nickname
            await conn.websocket.send_json({"type": "nickname_set", "nickname": nickname})

    elif msg_type == "ping":
        await conn.websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})

    else:
        await conn.websocket.send_json({"type": "error", "message": f"Unknown type: {msg_type}"})


# ── App ─────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _heartbeat_task
    _heartbeat_task = asyncio.create_task(heartbeat_loop())
    yield
    if _heartbeat_task:
        _heartbeat_task.cancel()


app = FastAPI(title="WebSocket Chat Server", lifespan=lifespan)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    connection_id = str(uuid.uuid4())
    conn = ConnectionState(connection_id=connection_id, websocket=ws)
    conn_manager.add(conn)

    # Send welcome
    await ws.send_json({
        "type": "welcome",
        "connection_id": connection_id,
        "rooms": room_manager.list_public_rooms(),
    })

    try:
        while True:
            raw = await ws.receive_text()
            await handle_ws_message(connection_id, raw)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        removed = conn_manager.remove(connection_id)
        if removed:
            removed.is_alive = False
            for rid in removed.rooms:
                room = room_manager.get_room(rid)
                if room:
                    room.connections.discard(connection_id)
                    await room_manager.broadcast_to_room(
                        rid,
                        {"type": "user_left", "room_id": rid, "nickname": removed.nickname or "Anonymous", "online_count": len(room.connections)},
                        conn_manager,
                    )


# ── REST Endpoints ──────────────────────────────────────────────────────


@app.get("/rooms")
async def list_rooms():
    return room_manager.list_public_rooms()


@app.get("/rooms/{room_id}/history")
async def get_room_history(room_id: str, limit: int = Query(20, ge=1, le=100)):
    room = room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    messages = room.get_recent_messages(limit)
    return {"room_id": room_id, "messages": messages, "total": len(messages)}


@app.get("/rooms/{room_id}/online")
async def get_online_users(room_id: str):
    room = room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    users = []
    for cid in room.connections:
        conn = conn_manager.get(cid)
        if conn and conn.is_alive:
            users.append({
                "connection_id": conn.connection_id,
                "nickname": conn.nickname,
                "connected_at": conn.connected_at.isoformat(),
                "last_activity": conn.last_activity.isoformat(),
            })
    return {"room_id": room_id, "online_count": len(users), "users": users}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
