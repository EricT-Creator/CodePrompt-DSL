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


def resolve_room(rid: str) -> Room:
    if rid not in rooms:
        rooms[rid] = Room()
    return rooms[rid]


def ts() -> str:
    return datetime.now(timezone.utc).isoformat()


async def distribute(room: Room, msg: dict) -> None:
    raw = json.dumps(msg)
    for ws in list(room.connections):
        try:
            await ws.send_text(raw)
        except Exception:
            room.connections.discard(ws)
            room.nicknames.pop(ws, None)


def persist(room: Room, entry: dict) -> None:
    room.history.append(entry)
    if len(room.history) > 100:
        room.history = room.history[-100:]


@app.websocket("/ws/{room_id}")
async def handle_ws(websocket: WebSocket, room_id: str, nickname: str = Query(default="")):
    await websocket.accept()

    if not nickname.strip():
        await websocket.send_text(json.dumps({"error": "nickname required"}))
        await websocket.close(code=1008)
        return

    nick = nickname.strip()
    room = resolve_room(room_id)
    room.connections.add(websocket)
    room.nicknames[websocket] = nick

    join = {"sender": "system", "text": f"{nick} joined", "timestamp": ts()}
    await distribute(room, join)
    persist(room, join)

    try:
        while True:
            text = await websocket.receive_text()
            payload = {"sender": nick, "text": text, "timestamp": ts()}
            await distribute(room, payload)
            persist(room, payload)
    except WebSocketDisconnect:
        room.connections.discard(websocket)
        room.nicknames.pop(websocket, None)
        leave = {"sender": "system", "text": f"{nick} left", "timestamp": ts()}
        await distribute(room, leave)
        persist(room, leave)
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
