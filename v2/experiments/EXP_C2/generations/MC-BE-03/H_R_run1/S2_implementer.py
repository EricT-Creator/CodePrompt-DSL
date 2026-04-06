import json
from datetime import datetime, timezone
from dataclasses import dataclass, field

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.responses import JSONResponse


@dataclass
class Room:
    connections: set = field(default_factory=set)
    nicknames: dict = field(default_factory=dict)
    history: list = field(default_factory=list)


app = FastAPI()
rooms: dict[str, Room] = {}


def get_or_create_room(room_id: str) -> Room:
    if room_id not in rooms:
        rooms[room_id] = Room()
    return rooms[room_id]


async def broadcast(room: Room, payload: dict, exclude: WebSocket | None = None) -> None:
    message_str = json.dumps(payload)
    targets = list(room.connections)
    for ws in targets:
        if ws is exclude:
            continue
        try:
            await ws.send_text(message_str)
        except Exception:
            room.connections.discard(ws)
            room.nicknames.pop(ws, None)


def store_message(room: Room, payload: dict) -> None:
    room.history.append(payload)
    if len(room.history) > 100:
        room.history = room.history[-100:]


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, nickname: str = Query(default="")):
    if not nickname or not nickname.strip():
        await websocket.accept()
        await websocket.send_text(json.dumps({"error": "nickname is required"}))
        await websocket.close(code=1008)
        return

    if not room_id or not room_id.strip():
        await websocket.accept()
        await websocket.send_text(json.dumps({"error": "invalid room_id"}))
        await websocket.close(code=1008)
        return

    await websocket.accept()
    room = get_or_create_room(room_id)
    room.connections.add(websocket)
    room.nicknames[websocket] = nickname

    join_payload = {
        "sender": "system",
        "text": f"{nickname} joined the room",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await broadcast(room, join_payload)
    store_message(room, join_payload)

    try:
        while True:
            data = await websocket.receive_text()
            payload = {
                "sender": nickname,
                "text": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await broadcast(room, payload)
            store_message(room, payload)
    except WebSocketDisconnect:
        room.connections.discard(websocket)
        room.nicknames.pop(websocket, None)
        leave_payload = {
            "sender": "system",
            "text": f"{nickname} left the room",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await broadcast(room, leave_payload)
        store_message(room, leave_payload)
    except Exception:
        room.connections.discard(websocket)
        room.nicknames.pop(websocket, None)
        try:
            await websocket.close()
        except Exception:
            pass


@app.get("/rooms/{room_id}/history")
async def get_history(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    return JSONResponse(content=rooms[room_id].history)


@app.get("/rooms/{room_id}/users")
async def get_users(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    return JSONResponse(content=list(rooms[room_id].nicknames.values()))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
