# EXP-C Phase 3 — DeepSeek-V3.2 S3 Auditor (NLf × RRS)
## Task: MC-BE-03

## Constraint Review
- C1 (Python + FastAPI): PASS — 使用FastAPI框架
- C2 (Set iteration broadcast, no async queue): PASS — 通过迭代活动连接集进行广播，无async.Queue
- C3 (fastapi + uvicorn only): PASS — 仅使用fastapi和uvicorn，无其他第三方包
- C4 (Single file): PASS — 所有代码在一个Python文件中
- C5 (Message history list ≤100): PASS — 每个房间的消息历史存储在列表中，上限100条
- C6 (Code only): FAIL — 审查报告包含解释文本，而不仅仅是代码

## Functionality Assessment (0-5)
Score: 4 — 实现了一个多房间WebSocket聊天服务器，包含用户连接、消息广播、房间管理、消息历史等功能。通过迭代连接集进行广播，符合不使用异步队列的要求。消息历史限制为100条。系统功能完整，但审查报告违反了"只输出代码"的要求。

## Corrected Code
由于C6约束失败（审查报告包含解释文本而非仅代码），以下是修复后的完整.py文件。但请注意，审查报告本身仍需要包含解释，这是一个内在矛盾：

```py
"""WebSocket Chat Server with FastAPI — multi-room, broadcast by iterating connections."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel


# ── Data Structures ──────────────────────────────────────────────────────────


class UserInfo:
    __slots__ = ("nickname", "room_id", "connected_at")

    def __init__(self, nickname: str, room_id: str) -> None:
        self.nickname: str = nickname
        self.room_id: str = room_id
        self.connected_at: str = datetime.now(timezone.utc).isoformat()


class Message:
    __slots__ = ("id", "room_id", "nickname", "content", "timestamp", "type")

    def __init__(
        self,
        room_id: str,
        nickname: str,
        content: str,
        msg_type: str = "user",
    ) -> None:
        self.id: str = str(uuid.uuid4())
        self.room_id: str = room_id
        self.nickname: str = nickname
        self.content: str = content
        self.timestamp: str = datetime.now(timezone.utc).isoformat()
        self.type: str = msg_type

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "room_id": self.room_id,
            "nickname": self.nickname,
            "content": self.content,
            "timestamp": self.timestamp,
            "type": self.type,
        }


# ── Global State ─────────────────────────────────────────────────────────────

active_connections: dict[str, set[WebSocket]] = {}
user_info_map: dict[WebSocket, UserInfo] = {}
message_history: dict[str, list[Message]] = {}
room_list: set[str] = {"general", "random", "help"}


# ── Connection Manager ───────────────────────────────────────────────────────


class ConnectionManager:
    @staticmethod
    async def connect(websocket: WebSocket, nickname: str, room_id: str) -> None:
        await websocket.accept()
        user_info = UserInfo(nickname, room_id)
        user_info_map[websocket] = user_info

        if room_id not in active_connections:
            active_connections[room_id] = set()
            message_history[room_id] = []
            room_list.add(room_id)

        active_connections[room_id].add(websocket)

        # Broadcast join message
        join_msg = Message(
            room_id,
            "system",
            f"{nickname} joined the room",
            "system",
        )
        message_history[room_id].append(join_msg)
        if len(message_history[room_id]) > 100:
            message_history[room_id].pop(0)

        await ConnectionManager.broadcast_to_room(room_id, join_msg.to_dict())

        # Send room history to new user
        history = [msg.to_dict() for msg in message_history[room_id][-20:]]
        await websocket.send_json(
            {
                "type": "history",
                "room_id": room_id,
                "messages": history,
            }
        )

    @staticmethod
    async def disconnect(websocket: WebSocket) -> None:
        if websocket not in user_info_map:
            return

        user_info = user_info_map[websocket]
        room_id = user_info.room_id
        nickname = user_info.nickname

        # Remove from active connections
        if room_id in active_connections:
            active_connections[room_id].discard(websocket)
            if not active_connections[room_id]:
                del active_connections[room_id]

        # Remove user info
        del user_info_map[websocket]

        # Broadcast leave message
        leave_msg = Message(
            room_id,
            "system",
            f"{nickname} left the room",
            "system",
        )
        if room_id in message_history:
            message_history[room_id].append(leave_msg)
            if len(message_history[room_id]) > 100:
                message_history[room_id].pop(0)

        await ConnectionManager.broadcast_to_room(room_id, leave_msg.to_dict())

    @staticmethod
    async def broadcast_to_room(room_id: str, message: dict[str, Any]) -> None:
        """Broadcast by iterating over active connections in the room."""
        if room_id not in active_connections:
            return

        # Iterate over set of connections
        disconnected = []
        for connection in active_connections[room_id]:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected sockets
        for connection in disconnected:
            active_connections[room_id].discard(connection)
            if connection in user_info_map:
                del user_info_map[connection]

    @staticmethod
    async def send_personal_message(websocket: WebSocket, message: dict[str, Any]) -> None:
        try:
            await websocket.send_json(message)
        except Exception:
            pass


# ── Pydantic Models ──────────────────────────────────────────────────────────


class ChatMessage(BaseModel):
    content: str
    room_id: str
    nickname: str


class JoinRoomRequest(BaseModel):
    nickname: str
    room_id: str


class RoomInfo(BaseModel):
    room_id: str
    user_count: int
    message_count: int


# ── FastAPI App ──────────────────────────────────────────────────────────────


app = FastAPI(title="WebSocket Chat Server")
manager = ConnectionManager()


# ── HTTP Endpoints ───────────────────────────────────────────────────────────


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "WebSocket Chat Server"}


@app.get("/rooms")
async def list_rooms() -> list[RoomInfo]:
    rooms = []
    for room_id in sorted(room_list):
        user_count = len(active_connections.get(room_id, set()))
        msg_count = len(message_history.get(room_id, []))
        rooms.append(
            RoomInfo(
                room_id=room_id,
                user_count=user_count,
                message_count=msg_count,
            )
        )
    return rooms


@app.get("/rooms/{room_id}/history")
async def get_room_history(room_id: str, limit: int = 50) -> dict[str, Any]:
    if room_id not in message_history:
        raise HTTPException(status_code=404, detail="Room not found")

    messages = message_history[room_id][-limit:]
    return {
        "room_id": room_id,
        "messages": [msg.to_dict() for msg in messages],
        "total": len(message_history[room_id]),
    }


# ── WebSocket Endpoint ───────────────────────────────────────────────────────


@app.websocket("/ws/{nickname}/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    nickname: str,
    room_id: str,
) -> None:
    """Main WebSocket endpoint for chat."""
    if not nickname or len(nickname) > 30:
        await websocket.close(code=1008, reason="Invalid nickname")
        return

    if not room_id or len(room_id) > 50:
        await websocket.close(code=1008, reason="Invalid room ID")
        return

    await manager.connect(websocket, nickname, room_id)

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "message":
                content = data.get("content", "").strip()
                if not content or len(content) > 500:
                    continue

                # Create and store message
                msg = Message(room_id, nickname, content)
                message_history[room_id].append(msg)
                if len(message_history[room_id]) > 100:
                    message_history[room_id].pop(0)

                # Broadcast to room
                await manager.broadcast_to_room(room_id, msg.to_dict())

            elif data.get("type") == "ping":
                await manager.send_personal_message(
                    websocket,
                    {"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()},
                )

            elif data.get("type") == "typing":
                typing_msg = {
                    "type": "typing",
                    "room_id": room_id,
                    "nickname": nickname,
                    "is_typing": data.get("is_typing", False),
                }
                await manager.broadcast_to_room(room_id, typing_msg)

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)


# ── Main ─────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**注意**: 代码已按照约束要求修复，通过迭代连接集进行广播而非使用异步队列，消息历史限制为100条，所有功能在一个文件中实现。