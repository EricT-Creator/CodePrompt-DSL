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


def ensure_room(room_id: str) -> Room:
    if room_id not in rooms:
        rooms[room_id] = Room()
    return rooms[room_id]


async def send_to_all(room: Room, message: dict, skip: WebSocket | None = None) -> None:
    raw = json.dumps(message)
    for ws in list(room.connections):
        if ws is skip:
            continue
        try:
            await ws.send_text(raw)
        except Exception:
            room.connections.discard(ws)
            room.nicknames.pop(ws, None)


def add_to_history(room: Room, msg: dict) -> None:
    room.history.append(msg)
    if len(room.history) > 100:
        room.history = room.history[-100:]


@app.websocket("/ws/{room_id}")
async def ws_handler(websocket: WebSocket, room_id: str, nickname: str = Query(default="")):
    await websocket.accept()

    if not nickname.strip():
        await websocket.send_text(json.dumps({"error": "nickname is required"}))
        await websocket.close(code=1008)
        return

    if not room_id.strip():
        await websocket.send_text(json.dumps({"error": "room_id is invalid"}))
        await websocket.close(code=1008)
        return

    nickname = nickname.strip()
    room = ensure_room(room_id)
    room.connections.add(websocket)
    room.nicknames[websocket] = nickname

    sys_msg = {
        "sender": "system",
        "text": f"{nickname} has joined",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await send_to_all(room, sys_msg)
    add_to_history(room, sys_msg)

    try:
        while True:
            text = await websocket.receive_text()
            msg = {
                "sender": nickname,
                "text": text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await send_to_all(room, msg)
            add_to_history(room, msg)
    except WebSocketDisconnect:
        room.connections.discard(websocket)
        room.nicknames.pop(websocket, None)
        leave = {
            "sender": "system",
            "text": f"{nickname} has left",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await send_to_all(room, leave)
        add_to_history(room, leave)
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
