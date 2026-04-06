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


def get_room(room_id: str) -> Room:
    if room_id not in rooms:
        rooms[room_id] = Room()
    return rooms[room_id]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def broadcast_to_room(room: Room, payload: dict) -> None:
    text = json.dumps(payload)
    peers = list(room.connections)
    for ws in peers:
        try:
            await ws.send_text(text)
        except Exception:
            room.connections.discard(ws)
            room.nicknames.pop(ws, None)


def record_message(room: Room, payload: dict) -> None:
    room.history.append(payload)
    if len(room.history) > 100:
        room.history = room.history[-100:]


@app.websocket("/ws/{room_id}")
async def websocket_chat(websocket: WebSocket, room_id: str, nickname: str = Query(default="")):
    if not nickname or not nickname.strip():
        await websocket.accept()
        await websocket.send_text(json.dumps({"error": "nickname is required"}))
        await websocket.close(code=1008)
        return

    await websocket.accept()
    room = get_room(room_id)
    room.connections.add(websocket)
    room.nicknames[websocket] = nickname

    sys_msg = {"sender": "system", "text": f"{nickname} has joined", "timestamp": utc_now_iso()}
    await broadcast_to_room(room, sys_msg)
    record_message(room, sys_msg)

    try:
        while True:
            content = await websocket.receive_text()
            msg = {"sender": nickname, "text": content, "timestamp": utc_now_iso()}
            await broadcast_to_room(room, msg)
            record_message(room, msg)
    except WebSocketDisconnect:
        room.connections.discard(websocket)
        room.nicknames.pop(websocket, None)
        leave = {"sender": "system", "text": f"{nickname} left", "timestamp": utc_now_iso()}
        await broadcast_to_room(room, leave)
        record_message(room, leave)
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
