import asyncio
import time
from collections import deque
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI(title="WebSocket Room Chat")


class RoomState:
    def __init__(self) -> None:
        self.clients: dict[WebSocket, str] = {}
        self.history: deque[dict[str, Any]] = deque(maxlen=50)
        self.lock = asyncio.Lock()


rooms: dict[str, RoomState] = {}
rooms_lock = asyncio.Lock()


async def get_or_create_room(room_name: str) -> RoomState:
    async with rooms_lock:
        room = rooms.get(room_name)
        if room is None:
            room = RoomState()
            rooms[room_name] = room
        return room


async def remove_room_if_empty(room_name: str) -> None:
    async with rooms_lock:
        room = rooms.get(room_name)
        if room is not None and not room.clients:
            rooms.pop(room_name, None)


async def add_history(room_name: str, payload: dict[str, Any]) -> None:
    room = rooms.get(room_name)
    if room is None:
        return
    async with room.lock:
        room.history.append(payload)


async def broadcast(room_name: str, payload: dict[str, Any]) -> None:
    room = rooms.get(room_name)
    if room is None:
        return

    async with room.lock:
        targets = list(room.clients.keys())

    disconnected: list[WebSocket] = []
    for websocket in targets:
        try:
            await websocket.send_json(payload)
        except Exception:
            disconnected.append(websocket)

    if disconnected:
        async with room.lock:
            for websocket in disconnected:
                room.clients.pop(websocket, None)
        await remove_room_if_empty(room_name)


@app.get("/rooms")
async def list_rooms():
    async with rooms_lock:
        snapshot = sorted(rooms.items(), key=lambda item: item[0])

    data = []
    for room_name, room in snapshot:
        async with room.lock:
            users = len(room.clients)
            history_size = len(room.history)
        if users > 0:
            data.append({"room": room_name, "users": users, "history": history_size})

    return {"rooms": data}


@app.websocket("/ws/{room_name}")
async def websocket_chat(websocket: WebSocket, room_name: str):
    await websocket.accept()
    room = await get_or_create_room(room_name)

    await websocket.send_json(
        {
            "type": "system",
            "message": "请先发送昵称作为第一条消息。",
            "room": room_name,
        }
    )

    nickname = "访客"
    try:
        nickname_candidate = (await websocket.receive_text()).strip()
        nickname = nickname_candidate or f"guest-{int(time.time())}"

        async with room.lock:
            room.clients[websocket] = nickname
            history_snapshot = list(room.history)

        await websocket.send_json(
            {
                "type": "history",
                "room": room_name,
                "items": history_snapshot,
            }
        )

        join_payload = {
            "type": "system",
            "room": room_name,
            "nickname": nickname,
            "message": f"{nickname} 加入了房间",
            "timestamp": int(time.time()),
        }
        await add_history(room_name, join_payload)
        await broadcast(room_name, join_payload)

        while True:
            text = (await websocket.receive_text()).strip()
            if not text:
                continue

            payload = {
                "type": "message",
                "room": room_name,
                "nickname": nickname,
                "message": text,
                "timestamp": int(time.time()),
            }
            await add_history(room_name, payload)
            await broadcast(room_name, payload)
    except WebSocketDisconnect:
        pass
    finally:
        async with room.lock:
            room.clients.pop(websocket, None)
            remaining = len(room.clients)

        if remaining > 0:
            leave_payload = {
                "type": "system",
                "room": room_name,
                "nickname": nickname,
                "message": f"{nickname} 离开了房间",
                "timestamp": int(time.time()),
            }
            await add_history(room_name, leave_payload)
            await broadcast(room_name, leave_payload)

        await remove_room_if_empty(room_name)


@app.get("/")
async def index():
    return {
        "message": "Connect to /ws/{room_name} and send your nickname as the first message.",
        "endpoints": ["GET /rooms", "WS /ws/{room_name}"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
