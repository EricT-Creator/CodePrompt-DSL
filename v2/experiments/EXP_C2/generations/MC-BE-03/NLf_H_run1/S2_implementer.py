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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def lazy_room(rid: str) -> Room:
    if rid not in rooms:
        rooms[rid] = Room()
    return rooms[rid]


async def send_to_all(room: Room, msg: dict) -> None:
    text = json.dumps(msg)
    for ws in list(room.connections):
        try:
            await ws.send_text(text)
        except Exception:
            room.connections.discard(ws)
            room.nicknames.pop(ws, None)


def save_msg(room: Room, msg: dict) -> None:
    room.history.append(msg)
    if len(room.history) > 100:
        room.history = room.history[-100:]


@app.websocket("/ws/{room_id}")
async def ws_chat(websocket: WebSocket, room_id: str, nickname: str = Query(default="")):
    if not nickname or not nickname.strip():
        await websocket.accept()
        await websocket.send_text(json.dumps({"error": "nickname is required"}))
        await websocket.close(code=1008)
        return

    await websocket.accept()
    room = lazy_room(room_id)
    room.connections.add(websocket)
    room.nicknames[websocket] = nickname

    join = {"sender": "system", "text": f"{nickname} joined", "timestamp": now_iso()}
    await send_to_all(room, join)
    save_msg(room, join)

    try:
        while True:
            raw = await websocket.receive_text()
            payload = {"sender": nickname, "text": raw, "timestamp": now_iso()}
            await send_to_all(room, payload)
            save_msg(room, payload)
    except WebSocketDisconnect:
        room.connections.discard(websocket)
        room.nicknames.pop(websocket, None)
        leave = {"sender": "system", "text": f"{nickname} left", "timestamp": now_iso()}
        await send_to_all(room, leave)
        save_msg(room, leave)
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
