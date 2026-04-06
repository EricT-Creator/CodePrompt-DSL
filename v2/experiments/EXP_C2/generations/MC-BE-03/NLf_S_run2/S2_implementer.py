import json
from datetime import datetime, timezone
from dataclasses import dataclass, field
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.responses import JSONResponse


app = FastAPI()


@dataclass
class Room:
    connections: set = field(default_factory=set)
    nicknames: dict = field(default_factory=dict)
    history: list = field(default_factory=list)


rooms: dict[str, Room] = {}


def _room(rid: str) -> Room:
    if rid not in rooms:
        rooms[rid] = Room()
    return rooms[rid]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _send_all(room: Room, payload: dict) -> None:
    encoded = json.dumps(payload)
    peers = list(room.connections)
    for peer in peers:
        try:
            await peer.send_text(encoded)
        except Exception:
            room.connections.discard(peer)
            room.nicknames.pop(peer, None)


def _save(room: Room, msg: dict) -> None:
    room.history.append(msg)
    if len(room.history) > 100:
        room.history = room.history[-100:]


@app.websocket("/ws/{room_id}")
async def ws_endpoint(websocket: WebSocket, room_id: str, nickname: str = Query(default="")):
    await websocket.accept()

    if not nickname.strip():
        await websocket.send_text(json.dumps({"error": "nickname is required"}))
        await websocket.close(code=1008)
        return

    name = nickname.strip()
    room = _room(room_id)
    room.connections.add(websocket)
    room.nicknames[websocket] = name

    join_msg = {"sender": "system", "text": f"{name} has joined", "timestamp": _now()}
    await _send_all(room, join_msg)
    _save(room, join_msg)

    try:
        while True:
            text = await websocket.receive_text()
            msg = {"sender": name, "text": text, "timestamp": _now()}
            await _send_all(room, msg)
            _save(room, msg)
    except WebSocketDisconnect:
        room.connections.discard(websocket)
        room.nicknames.pop(websocket, None)
        leave_msg = {"sender": "system", "text": f"{name} has left", "timestamp": _now()}
        await _send_all(room, leave_msg)
        _save(room, leave_msg)
    except Exception:
        room.connections.discard(websocket)
        room.nicknames.pop(websocket, None)
        try:
            await websocket.close()
        except Exception:
            pass


@app.get("/rooms/{room_id}/history")
async def history_endpoint(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    return JSONResponse(content=rooms[room_id].history)


@app.get("/rooms/{room_id}/users")
async def users_endpoint(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    return JSONResponse(content=list(rooms[room_id].nicknames.values()))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
