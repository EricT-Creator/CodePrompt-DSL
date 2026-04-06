from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Set
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI(title="WebSocket Multi-Room Chat")


@dataclass
class RoomState:
    connections: Set[WebSocket] = field(default_factory=set)
    nicknames: Dict[WebSocket, str] = field(default_factory=dict)
    history: Deque[Dict[str, Any]] = field(default_factory=lambda: deque(maxlen=50))


rooms: Dict[str, RoomState] = {}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_room(room_name: str) -> RoomState:
    if room_name not in rooms:
        rooms[room_name] = RoomState()
    return rooms[room_name]


def serialize_rooms() -> List[Dict[str, Any]]:
    payload: List[Dict[str, Any]] = []
    for room_name in sorted(rooms.keys()):
        room = rooms[room_name]
        payload.append(
            {
                "room": room_name,
                "user_count": len(room.connections),
                "history_size": len(room.history),
            }
        )
    return payload


async def broadcast(room_name: str, event: Dict[str, Any]) -> None:
    room = rooms.get(room_name)
    if not room:
        return

    disconnected: List[WebSocket] = []
    for connection in set(room.connections):
        try:
            await connection.send_json(event)
        except Exception:
            disconnected.append(connection)

    for connection in disconnected:
        room.connections.discard(connection)
        room.nicknames.pop(connection, None)

    if not room.connections:
        rooms.pop(room_name, None)


@app.get("/")
def root() -> Dict[str, Any]:
    return {
        "message": "Connect with WebSocket at /ws/{room_name}?nickname=YourName",
        "rooms_endpoint": "/rooms",
    }


@app.get("/rooms")
def list_rooms() -> Dict[str, Any]:
    return {"rooms": serialize_rooms()}


@app.websocket("/ws/{room_name}")
async def websocket_chat(websocket: WebSocket, room_name: str) -> None:
    await websocket.accept()

    nickname = websocket.query_params.get("nickname") or f"Guest-{uuid4().hex[:6]}"
    room = get_room(room_name)
    room.connections.add(websocket)
    room.nicknames[websocket] = nickname

    history_snapshot = list(room.history)
    await websocket.send_json(
        {
            "type": "history",
            "room": room_name,
            "messages": history_snapshot,
            "user_count": len(room.connections),
        }
    )

    join_event = {
        "type": "system",
        "room": room_name,
        "message": f"{nickname} joined the room",
        "timestamp": utc_now(),
        "user_count": len(room.connections),
    }
    room.history.append(join_event)
    await broadcast(room_name, join_event)

    try:
        while True:
            message = (await websocket.receive_text()).strip()
            if not message:
                continue

            chat_event = {
                "type": "message",
                "room": room_name,
                "nickname": nickname,
                "message": message,
                "timestamp": utc_now(),
                "user_count": len(room.connections),
            }
            room.history.append(chat_event)
            await broadcast(room_name, chat_event)
    except WebSocketDisconnect:
        pass
    finally:
        room = rooms.get(room_name)
        if not room:
            return

        room.connections.discard(websocket)
        room.nicknames.pop(websocket, None)

        leave_event = {
            "type": "system",
            "room": room_name,
            "message": f"{nickname} left the room",
            "timestamp": utc_now(),
            "user_count": len(room.connections),
        }

        room.history.append(leave_event)
        if room.connections:
            await broadcast(room_name, leave_event)
        else:
            rooms.pop(room_name, None)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
