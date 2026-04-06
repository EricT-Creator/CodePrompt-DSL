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


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_room(rid: str) -> Room:
    if rid not in rooms:
        rooms[rid] = Room()
    return rooms[rid]


async def _send_all(room: Room, data: dict) -> None:
    encoded = json.dumps(data)
    for ws in list(room.connections):
        try:
            await ws.send_text(encoded)
        except Exception:
            room.connections.discard(ws)
            room.nicknames.pop(ws, None)


def _add_to_history(room: Room, msg: dict) -> None:
    room.history.append(msg)
    if len(room.history) > 100:
        room.history = room.history[-100:]


@app.websocket("/ws/{room_id}")
async def websocket_route(websocket: WebSocket, room_id: str, nickname: str = Query(default="")):
    if not nickname or not nickname.strip():
        await websocket.accept()
        await websocket.send_text(json.dumps({"error": "nickname is required"}))
        await websocket.close(code=1008)
        return

    await websocket.accept()
    room = _ensure_room(room_id)
    room.connections.add(websocket)
    room.nicknames[websocket] = nickname

    arrival = {"sender": "system", "text": f"{nickname} joined", "timestamp": _utc()}
    await _send_all(room, arrival)
    _add_to_history(room, arrival)

    try:
        while True:
            content = await websocket.receive_text()
            message = {"sender": nickname, "text": content, "timestamp": _utc()}
            await _send_all(room, message)
            _add_to_history(room, message)
    except WebSocketDisconnect:
        room.connections.discard(websocket)
        room.nicknames.pop(websocket, None)
        departure = {"sender": "system", "text": f"{nickname} left", "timestamp": _utc()}
        await _send_all(room, departure)
        _add_to_history(room, departure)
    except Exception:
        room.connections.discard(websocket)
        room.nicknames.pop(websocket, None)
        try:
            await websocket.close()
        except Exception:
            pass


@app.get("/rooms/{room_id}/history")
async def room_history(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    return JSONResponse(content=rooms[room_id].history)


@app.get("/rooms/{room_id}/users")
async def room_users(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    return JSONResponse(content=list(rooms[room_id].nicknames.values()))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
