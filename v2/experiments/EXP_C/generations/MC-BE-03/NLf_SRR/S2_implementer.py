from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import uvicorn


# ── Data models ─────────────────────────────────────────────────────────

@dataclass
class Message:
    message_id: str
    client_id: str
    nickname: str
    room_id: str
    content: str
    timestamp: str
    message_type: str = "chat"

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "client_id": self.client_id,
            "nickname": self.nickname,
            "room_id": self.room_id,
            "content": self.content,
            "timestamp": self.timestamp,
            "message_type": self.message_type,
        }


@dataclass
class ConnectionInfo:
    websocket: WebSocket
    client_id: str
    nickname: str
    room_id: str
    connected_at: str


# ── Chat Server ─────────────────────────────────────────────────────────

class ChatServer:
    MAX_HISTORY = 100

    def __init__(self) -> None:
        self.connections: dict[str, ConnectionInfo] = {}
        self.rooms: dict[str, set[str]] = {}
        self.history: dict[str, list[Message]] = {}

    # ── Room management ─────────────────────────────────────────────────

    def _ensure_room(self, room_id: str) -> None:
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
            self.history[room_id] = []

    async def join_room(self, room_id: str, client_id: str) -> None:
        self._ensure_room(room_id)
        self.rooms[room_id].add(client_id)
        conn = self.connections.get(client_id)
        nickname = conn.nickname if conn else client_id
        await self._broadcast(room_id, {
            "type": "user_joined",
            "client_id": client_id,
            "nickname": nickname,
            "timestamp": datetime.utcnow().isoformat(),
            "online_count": len(self.rooms[room_id]),
        }, exclude=client_id)
        self._add_history(room_id, Message(
            message_id=str(uuid.uuid4()),
            client_id="system",
            nickname="System",
            room_id=room_id,
            content=f"{nickname} joined the room",
            timestamp=datetime.utcnow().isoformat(),
            message_type="system",
        ))

    async def leave_room(self, client_id: str, room_id: str) -> None:
        clients = self.rooms.get(room_id)
        if not clients:
            return
        clients.discard(client_id)
        conn = self.connections.get(client_id)
        nickname = conn.nickname if conn else client_id
        if clients:
            await self._broadcast(room_id, {
                "type": "user_left",
                "client_id": client_id,
                "nickname": nickname,
                "timestamp": datetime.utcnow().isoformat(),
                "online_count": len(clients),
            })
            self._add_history(room_id, Message(
                message_id=str(uuid.uuid4()),
                client_id="system",
                nickname="System",
                room_id=room_id,
                content=f"{nickname} left the room",
                timestamp=datetime.utcnow().isoformat(),
                message_type="system",
            ))
        else:
            del self.rooms[room_id]

    # ── Broadcast (iterate active connections) ──────────────────────────

    async def _broadcast(self, room_id: str, message: dict[str, Any], exclude: str | None = None) -> None:
        clients = self.rooms.get(room_id)
        if not clients:
            return
        dead: list[str] = []
        for cid in clients:
            if cid == exclude:
                continue
            conn = self.connections.get(cid)
            if conn:
                try:
                    await conn.websocket.send_json(message)
                except Exception:
                    dead.append(cid)
        for cid in dead:
            clients.discard(cid)
            self.connections.pop(cid, None)

    # ── History management ──────────────────────────────────────────────

    def _add_history(self, room_id: str, msg: Message) -> None:
        self._ensure_room(room_id)
        h = self.history[room_id]
        h.append(msg)
        if len(h) > self.MAX_HISTORY:
            self.history[room_id] = h[-self.MAX_HISTORY:]

    def get_history(self, room_id: str, limit: int = 50) -> list[dict]:
        h = self.history.get(room_id, [])
        return [m.to_dict() for m in h[-limit:]]

    # ── Message handling ────────────────────────────────────────────────

    async def handle_message(self, conn: ConnectionInfo, data: dict[str, Any]) -> None:
        mtype = data.get("type", "")

        if mtype == "chat_message":
            content = str(data.get("content", "")).strip()
            if not content:
                return
            msg = Message(
                message_id=str(uuid.uuid4()),
                client_id=conn.client_id,
                nickname=conn.nickname,
                room_id=conn.room_id,
                content=content,
                timestamp=datetime.utcnow().isoformat(),
            )
            self._add_history(conn.room_id, msg)
            await self._broadcast(conn.room_id, {
                "type": "chat_message",
                **msg.to_dict(),
            }, exclude=conn.client_id)
            await conn.websocket.send_json({"type": "message_sent", "message_id": msg.message_id, "timestamp": msg.timestamp})

        elif mtype == "typing_indicator":
            await self._broadcast(conn.room_id, {
                "type": "typing_indicator",
                "client_id": conn.client_id,
                "nickname": conn.nickname,
                "is_typing": data.get("is_typing", True),
            }, exclude=conn.client_id)

        elif mtype == "nickname_change":
            new_nick = str(data.get("nickname", "")).strip()
            if new_nick:
                old_nick = conn.nickname
                conn.nickname = new_nick
                await self._broadcast(conn.room_id, {
                    "type": "nickname_changed",
                    "client_id": conn.client_id,
                    "old_nickname": old_nick,
                    "new_nickname": new_nick,
                    "timestamp": datetime.utcnow().isoformat(),
                })

        else:
            await conn.websocket.send_json({"type": "error", "message": f"Unknown message type: {mtype}"})

    # ── Connection lifecycle ────────────────────────────────────────────

    async def connect(self, ws: WebSocket, client_id: str, nickname: str, room_id: str) -> None:
        await ws.accept()
        conn = ConnectionInfo(
            websocket=ws,
            client_id=client_id,
            nickname=nickname,
            room_id=room_id,
            connected_at=datetime.utcnow().isoformat(),
        )
        self.connections[client_id] = conn
        await self.join_room(room_id, client_id)

        history = self.get_history(room_id, 50)
        await ws.send_json({"type": "welcome", "room_id": room_id, "history": history, "online_count": len(self.rooms.get(room_id, set()))})

        try:
            while True:
                raw = await ws.receive_json()
                await self.handle_message(conn, raw)
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            await self.leave_room(client_id, room_id)
            self.connections.pop(client_id, None)


# ── FastAPI app ─────────────────────────────────────────────────────────

app = FastAPI(title="WebSocket Chat Server")
server = ChatServer()


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(ws: WebSocket, room_id: str, client_id: str | None = None, nickname: str | None = None) -> None:
    cid = client_id or str(uuid.uuid4())
    nick = nickname or f"User-{cid[:6]}"
    await server.connect(ws, cid, nick, room_id)


@app.get("/rooms/{room_id}/history")
async def get_room_history(room_id: str, limit: int = Query(50, ge=1, le=100)) -> dict:
    messages = server.get_history(room_id, limit)
    return {"room_id": room_id, "messages": messages, "total": len(messages)}


@app.get("/rooms")
async def list_rooms() -> dict:
    rooms = []
    for rid, clients in server.rooms.items():
        rooms.append({"room_id": rid, "online_count": len(clients)})
    return {"rooms": rooms}


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "total_connections": len(server.connections), "total_rooms": len(server.rooms)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
