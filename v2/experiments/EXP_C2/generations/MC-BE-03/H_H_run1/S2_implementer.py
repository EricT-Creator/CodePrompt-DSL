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


def ensure_room(room_id: str) -> Room:
    if room_id not in rooms:
        rooms[room_id] = Room()
    return rooms[room_id]


async def broadcast_message(room: Room, payload: dict) -> None:
    raw = json.dumps(payload)
    snapshot = list(room.connections)
    for conn in snapshot:
        try:
            await conn.send_text(raw)
        except Exception:
            room.connections.discard(conn)
            room.nicknames.pop(conn, None)


def append_history(room: Room, msg: dict) -> None:
    room.history.append(msg)
    if len(room.history) > 100:
        room.history = room.history[-100:]


@app.websocket("/ws/{room_id}")
async def ws_handler(websocket: WebSocket, room_id: str, nickname: str = Query(default="")):
    if not nickname.strip():
        await websocket.accept()
        await websocket.send_text(json.dumps({"error": "nickname is required"}))
        await websocket.close(code=1008)
        return

    if not room_id.strip():
        await websocket.accept()
        await websocket.send_text(json.dumps({"error": "invalid room_id"}))
        await websocket.close(code=1008)
        return

    await websocket.accept()
    room = ensure_room(room_id)
    room.connections.add(websocket)
    room.nicknames[websocket] = nickname

    join_msg = {
        "sender": "system",
        "text": f"{nickname} joined",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await broadcast_message(room, join_msg)
    append_history(room, join_msg)

    try:
        while True:
            text = await websocket.receive_text()
            msg = {
                "sender": nickname,
                "text": text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await broadcast_message(room, msg)
            append_history(room, msg)
    except WebSocketDisconnect:
        room.connections.discard(websocket)
        room.nicknames.pop(websocket, None)
        leave_msg = {
            "sender": "system",
            "text": f"{nickname} left",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await broadcast_message(room, leave_msg)
        append_history(room, leave_msg)
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
