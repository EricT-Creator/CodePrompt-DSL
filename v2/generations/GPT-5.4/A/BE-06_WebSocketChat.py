import asyncio
import time
from collections import deque
from typing import Deque, Dict, List, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI(title="WebSocket Chat")


class RoomState:
    def __init__(self) -> None:
        self.connections: Set[WebSocket] = set()
        self.nicknames: Dict[WebSocket, str] = {}
        self.history: Deque[Dict[str, str]] = deque(maxlen=50)


rooms: Dict[str, RoomState] = {}
rooms_lock = asyncio.Lock()


async def get_or_create_room(room_name: str) -> RoomState:
    async with rooms_lock:
        room = rooms.get(room_name)
        if room is None:
            room = RoomState()
            rooms[room_name] = room
        return room


async def remove_connection(room_name: str, websocket: WebSocket) -> None:
    async with rooms_lock:
        room = rooms.get(room_name)
        if room is None:
            return

        room.connections.discard(websocket)
        room.nicknames.pop(websocket, None)

        if not room.connections:
            rooms.pop(room_name, None)


async def broadcast(room_name: str, message: Dict[str, str]) -> None:
    async with rooms_lock:
        room = rooms.get(room_name)
        if room is None:
            return
        targets = list(room.connections)

    stale_connections: List[WebSocket] = []
    for connection in targets:
        try:
            await connection.send_json(message)
        except Exception:
            stale_connections.append(connection)

    for connection in stale_connections:
        await remove_connection(room_name, connection)


def system_message(text: str) -> Dict[str, str]:
    return {
        "type": "system",
        "nickname": "system",
        "message": text,
        "timestamp": str(int(time.time())),
    }


@app.get("/rooms")
async def list_rooms() -> Dict[str, List[Dict[str, int]]]:
    async with rooms_lock:
        room_list = [
            {"room": name, "users": len(room.connections)}
            for name, room in sorted(rooms.items(), key=lambda entry: entry[0])
        ]
    return {"rooms": room_list}


@app.websocket("/ws/{room_name}")
async def websocket_chat(websocket: WebSocket, room_name: str) -> None:
    await websocket.accept()
    room = await get_or_create_room(room_name)

    await websocket.send_json(
        {
            "type": "system",
            "message": "Send your nickname as the first message.",
            "timestamp": str(int(time.time())),
        }
    )

    nickname = ""
    try:
        nickname = (await websocket.receive_text()).strip() or "Anonymous"

        async with rooms_lock:
            room.connections.add(websocket)
            room.nicknames[websocket] = nickname
            history_snapshot = list(room.history)

        await websocket.send_json(
            {
                "type": "history",
                "room": room_name,
                "messages": history_snapshot,
            }
        )

        join_notice = system_message(f"{nickname} joined {room_name}")
        async with rooms_lock:
            current_room = rooms.get(room_name)
            if current_room is not None:
                current_room.history.append(join_notice)

        await broadcast(room_name, join_notice)

        while True:
            text = (await websocket.receive_text()).strip()
            if not text:
                continue

            payload = {
                "type": "chat",
                "room": room_name,
                "nickname": nickname,
                "message": text,
                "timestamp": str(int(time.time())),
            }

            async with rooms_lock:
                current_room = rooms.get(room_name)
                if current_room is not None:
                    current_room.history.append(payload)

            await broadcast(room_name, payload)
    except WebSocketDisconnect:
        pass
    finally:
        await remove_connection(room_name, websocket)
        if nickname:
            leave_notice = system_message(f"{nickname} left {room_name}")
            async with rooms_lock:
                current_room = rooms.get(room_name)
                if current_room is not None:
                    current_room.history.append(leave_notice)
            await broadcast(room_name, leave_notice)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
