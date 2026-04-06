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


def utcnow_str() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_or_init_room(room_id: str) -> Room:
    if room_id not in rooms:
        rooms[room_id] = Room()
    return rooms[room_id]


async def broadcast(room: Room, payload: dict) -> None:
    raw = json.dumps(payload)
    peers = list(room.connections)
    for peer in peers:
        try:
            await peer.send_text(raw)
        except Exception:
            room.connections.discard(peer)
            room.nicknames.pop(peer, None)


def push_history(room: Room, entry: dict) -> None:
    room.history.append(entry)
    if len(room.history) > 100:
        room.history = room.history[-100:]


@app.websocket("/ws/{room_id}")
async def ws_endpoint(websocket: WebSocket, room_id: str, nickname: str = Query(default="")):
    if not nickname.strip():
        await websocket.accept()
        await websocket.send_text(json.dumps({"error": "nickname missing"}))
        await websocket.close(code=1008)
        return

    await websocket.accept()
    room = get_or_init_room(room_id)
    room.connections.add(websocket)
    room.nicknames[websocket] = nickname

    greet = {"sender": "system", "text": f"{nickname} has joined", "timestamp": utcnow_str()}
    await broadcast(room, greet)
    push_history(room, greet)

    try:
        while True:
            text = await websocket.receive_text()
            msg = {"sender": nickname, "text": text, "timestamp": utcnow_str()}
            await broadcast(room, msg)
            push_history(room, msg)
    except WebSocketDisconnect:
        room.connections.discard(websocket)
        room.nicknames.pop(websocket, None)
        bye = {"sender": "system", "text": f"{nickname} left", "timestamp": utcnow_str()}
        await broadcast(room, bye)
        push_history(room, bye)
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
