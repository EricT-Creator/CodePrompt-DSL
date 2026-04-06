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


def iso_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def find_or_create_room(room_id: str) -> Room:
    if room_id not in rooms:
        rooms[room_id] = Room()
    return rooms[room_id]


async def fan_out(room: Room, message: dict) -> None:
    payload = json.dumps(message)
    targets = list(room.connections)
    for target in targets:
        try:
            await target.send_text(payload)
        except Exception:
            room.connections.discard(target)
            room.nicknames.pop(target, None)


def cap_history(room: Room, entry: dict) -> None:
    room.history.append(entry)
    if len(room.history) > 100:
        room.history = room.history[-100:]


@app.websocket("/ws/{room_id}")
async def websocket_handler(websocket: WebSocket, room_id: str, nickname: str = Query(default="")):
    if not nickname.strip():
        await websocket.accept()
        await websocket.send_text(json.dumps({"error": "nickname is required"}))
        await websocket.close(code=1008)
        return

    if not room_id.strip():
        await websocket.accept()
        await websocket.send_text(json.dumps({"error": "room_id is invalid"}))
        await websocket.close(code=1008)
        return

    await websocket.accept()
    room = find_or_create_room(room_id)
    room.connections.add(websocket)
    room.nicknames[websocket] = nickname

    announce = {"sender": "system", "text": f"{nickname} joined the room", "timestamp": iso_utc()}
    await fan_out(room, announce)
    cap_history(room, announce)

    try:
        while True:
            data = await websocket.receive_text()
            message = {"sender": nickname, "text": data, "timestamp": iso_utc()}
            await fan_out(room, message)
            cap_history(room, message)
    except WebSocketDisconnect:
        room.connections.discard(websocket)
        room.nicknames.pop(websocket, None)
        departure = {"sender": "system", "text": f"{nickname} left the room", "timestamp": iso_utc()}
        await fan_out(room, departure)
        cap_history(room, departure)
    except Exception:
        room.connections.discard(websocket)
        room.nicknames.pop(websocket, None)
        try:
            await websocket.close()
        except Exception:
            pass


@app.get("/rooms/{room_id}/history")
async def get_room_history(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    return JSONResponse(content=rooms[room_id].history)


@app.get("/rooms/{room_id}/users")
async def get_room_users(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    return JSONResponse(content=list(rooms[room_id].nicknames.values()))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
