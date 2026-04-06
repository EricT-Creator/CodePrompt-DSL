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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _room(room_id: str) -> Room:
    if room_id not in rooms:
        rooms[room_id] = Room()
    return rooms[room_id]


async def _broadcast(room: Room, payload: dict) -> None:
    data = json.dumps(payload)
    for ws in list(room.connections):
        try:
            await ws.send_text(data)
        except Exception:
            room.connections.discard(ws)
            room.nicknames.pop(ws, None)


def _store(room: Room, msg: dict) -> None:
    room.history.append(msg)
    if len(room.history) > 100:
        room.history = room.history[-100:]


@app.websocket("/ws/{room_id}")
async def chat_ws(websocket: WebSocket, room_id: str, nickname: str = Query(default="")):
    if not nickname or not nickname.strip():
        await websocket.accept()
        await websocket.send_text(json.dumps({"error": "nickname required"}))
        await websocket.close(code=1008)
        return

    if not room_id or not room_id.strip():
        await websocket.accept()
        await websocket.send_text(json.dumps({"error": "room_id invalid"}))
        await websocket.close(code=1008)
        return

    await websocket.accept()
    room = _room(room_id)
    room.connections.add(websocket)
    room.nicknames[websocket] = nickname

    join = {"sender": "system", "text": f"{nickname} joined", "timestamp": _now()}
    await _broadcast(room, join)
    _store(room, join)

    try:
        while True:
            msg_text = await websocket.receive_text()
            msg = {"sender": nickname, "text": msg_text, "timestamp": _now()}
            await _broadcast(room, msg)
            _store(room, msg)
    except WebSocketDisconnect:
        room.connections.discard(websocket)
        room.nicknames.pop(websocket, None)
        leave = {"sender": "system", "text": f"{nickname} left", "timestamp": _now()}
        await _broadcast(room, leave)
        _store(room, leave)
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
