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


def _get_room(rid: str) -> Room:
    if rid not in rooms:
        rooms[rid] = Room()
    return rooms[rid]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _broadcast(room: Room, payload: dict) -> None:
    data = json.dumps(payload)
    peers = list(room.connections)
    for peer in peers:
        try:
            await peer.send_text(data)
        except Exception:
            room.connections.discard(peer)
            room.nicknames.pop(peer, None)


def _record(room: Room, msg: dict) -> None:
    room.history.append(msg)
    if len(room.history) > 100:
        room.history = room.history[-100:]


@app.websocket("/ws/{room_id}")
async def ws_chat(websocket: WebSocket, room_id: str, nickname: str = Query(default="")):
    await websocket.accept()

    if not nickname or not nickname.strip():
        await websocket.send_text(json.dumps({"error": "nickname is required"}))
        await websocket.close(code=1008)
        return

    if not room_id or not room_id.strip():
        await websocket.send_text(json.dumps({"error": "invalid room_id"}))
        await websocket.close(code=1008)
        return

    nick = nickname.strip()
    room = _get_room(room_id)
    room.connections.add(websocket)
    room.nicknames[websocket] = nick

    join = {"sender": "system", "text": f"{nick} joined the room", "timestamp": _utcnow()}
    await _broadcast(room, join)
    _record(room, join)

    try:
        while True:
            raw = await websocket.receive_text()
            msg = {"sender": nick, "text": raw, "timestamp": _utcnow()}
            await _broadcast(room, msg)
            _record(room, msg)
    except WebSocketDisconnect:
        room.connections.discard(websocket)
        room.nicknames.pop(websocket, None)
        leave = {"sender": "system", "text": f"{nick} left the room", "timestamp": _utcnow()}
        await _broadcast(room, leave)
        _record(room, leave)
    except Exception:
        room.connections.discard(websocket)
        room.nicknames.pop(websocket, None)
        try:
            await websocket.close()
        except Exception:
            pass


@app.get("/rooms/{room_id}/history")
async def history(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    return JSONResponse(content=rooms[room_id].history)


@app.get("/rooms/{room_id}/users")
async def users(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    return JSONResponse(content=list(rooms[room_id].nicknames.values()))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
