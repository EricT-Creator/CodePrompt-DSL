"""MC-BE-03: WebSocket Chat Server — multi-room, broadcast via set iteration, history list ≤100"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

# ── Data structures ─────────────────────────────────────────────────

@dataclass
class ChatMessage:
    message_id: str
    room_id: str
    sender: str
    content: str
    timestamp: float
    message_type: str = "text"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "room_id": self.room_id,
            "sender": self.sender,
            "content": self.content,
            "timestamp": self.timestamp,
            "message_type": self.message_type,
        }


@dataclass
class ChatRoom:
    room_id: str
    messages: List[ChatMessage] = field(default_factory=list)
    users: Set[str] = field(default_factory=set)
    max_messages: int = 100
    created_at: float = field(default_factory=time.time)

    def add_message(self, msg: ChatMessage) -> None:
        self.messages.append(msg)
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def get_history(self, count: int = 50) -> List[Dict[str, Any]]:
        recent = self.messages[-count:] if count < len(self.messages) else self.messages
        return [m.to_dict() for m in recent]


# ── Connection & Room manager ───────────────────────────────────────

class ConnectionManager:
    def __init__(self) -> None:
        # room_id -> set of (websocket, nickname)
        self._rooms: Dict[str, Set[tuple]] = {}  # type: ignore[type-arg]
        self._ws_to_info: Dict[int, Dict[str, str]] = {}  # id(ws) -> {room_id, nickname}
        self._chat_rooms: Dict[str, ChatRoom] = {}

    def _ensure_room(self, room_id: str) -> ChatRoom:
        if room_id not in self._chat_rooms:
            self._chat_rooms[room_id] = ChatRoom(room_id=room_id)
        if room_id not in self._rooms:
            self._rooms[room_id] = set()
        return self._chat_rooms[room_id]

    async def connect(self, ws: WebSocket, room_id: str, nickname: str) -> None:
        await ws.accept()
        room = self._ensure_room(room_id)
        room.users.add(nickname)
        self._rooms[room_id].add((ws, nickname))
        self._ws_to_info[id(ws)] = {"room_id": room_id, "nickname": nickname}

        # Send history to the newly connected user
        history = room.get_history()
        await ws.send_json({"type": "history", "messages": history, "room_id": room_id})

        # Broadcast join
        await self._broadcast_to_room(
            room_id,
            {"type": "user_joined", "nickname": nickname, "timestamp": time.time(), "room_id": room_id},
            exclude_ws=ws,
        )

    async def disconnect(self, ws: WebSocket) -> None:
        info = self._ws_to_info.pop(id(ws), None)
        if not info:
            return
        room_id = info["room_id"]
        nickname = info["nickname"]

        if room_id in self._rooms:
            self._rooms[room_id].discard((ws, nickname))
            if not self._rooms[room_id]:
                del self._rooms[room_id]

        room = self._chat_rooms.get(room_id)
        if room:
            room.users.discard(nickname)

        await self._broadcast_to_room(
            room_id,
            {"type": "user_left", "nickname": nickname, "timestamp": time.time(), "room_id": room_id},
        )

    async def handle_message(self, ws: WebSocket, data: Dict[str, Any]) -> None:
        info = self._ws_to_info.get(id(ws))
        if not info:
            return

        room_id = info["room_id"]
        nickname = info["nickname"]
        msg_type = data.get("type", "chat_message")

        if msg_type == "chat_message":
            content = data.get("content", "")
            if not content.strip():
                return

            msg = ChatMessage(
                message_id=str(uuid.uuid4()),
                room_id=room_id,
                sender=nickname,
                content=content,
                timestamp=time.time(),
            )

            room = self._chat_rooms.get(room_id)
            if room:
                room.add_message(msg)

            broadcast_data = {"type": "chat_message", "message": msg.to_dict()}
            await self._broadcast_to_room(room_id, broadcast_data)

        elif msg_type == "typing":
            await self._broadcast_to_room(
                room_id,
                {"type": "typing", "nickname": nickname, "is_typing": data.get("is_typing", False)},
                exclude_ws=ws,
            )

    async def _broadcast_to_room(
        self,
        room_id: str,
        message: Dict[str, Any],
        exclude_ws: Optional[WebSocket] = None,
    ) -> None:
        conns = self._rooms.get(room_id, set())
        # Use set iteration as required by [BCAST]SET_ITER
        for ws, _nick in set(conns):
            if exclude_ws and ws is exclude_ws:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                pass  # connection may have closed

    def get_room_users(self, room_id: str) -> List[str]:
        room = self._chat_rooms.get(room_id)
        return sorted(room.users) if room else []

    def get_all_rooms(self) -> List[Dict[str, Any]]:
        result = []
        for rid, room in self._chat_rooms.items():
            result.append({
                "room_id": rid,
                "user_count": len(room.users),
                "message_count": len(room.messages),
                "created_at": room.created_at,
            })
        return result


# ── FastAPI app ─────────────────────────────────────────────────────

app = FastAPI(title="WebSocket Chat Server")
manager = ConnectionManager()


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(ws: WebSocket, room_id: str, nickname: str = "Anonymous") -> None:
    await manager.connect(ws, room_id, nickname)
    try:
        while True:
            data = await ws.receive_json()
            await manager.handle_message(ws, data)
    except WebSocketDisconnect:
        await manager.disconnect(ws)
    except Exception:
        await manager.disconnect(ws)


# ── REST endpoints ──────────────────────────────────────────────────

@app.get("/api/v1/rooms")
async def list_rooms() -> Dict[str, Any]:
    return {"rooms": manager.get_all_rooms()}


@app.get("/api/v1/rooms/{room_id}/users")
async def room_users(room_id: str) -> Dict[str, Any]:
    users = manager.get_room_users(room_id)
    return {"room_id": room_id, "users": users, "count": len(users)}


@app.get("/api/v1/rooms/{room_id}/history")
async def room_history(room_id: str, count: int = 50) -> Dict[str, Any]:
    room = manager._chat_rooms.get(room_id)
    if not room:
        return {"room_id": room_id, "messages": [], "count": 0}
    messages = room.get_history(count)
    return {"room_id": room_id, "messages": messages, "count": len(messages)}


@app.get("/api/v1/health")
async def health() -> Dict[str, str]:
    return {"status": "healthy"}
