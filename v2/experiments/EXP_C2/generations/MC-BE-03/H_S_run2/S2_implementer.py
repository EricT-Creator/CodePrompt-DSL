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


def get_room(room_id: str) -> Room:
    if room_id not in rooms:
        rooms[room_id] = Room()
    return rooms[room_id]


async def broadcast_message(room: Room, payload: dict) -> None:
    encoded = json.dumps(payload)
    targets = list(room.connections)
    for ws in targets:
        try:
            await ws.send_text(encoded)
        except Exception:
            room.connections.discard(ws)
            room.nicknames.pop(ws, None)


def append_history(room: Room, entry: dict) -> None:
    room.history.append(entry)
    if len(room.history) > 100:
        room.history = room.history[-100:]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.websocket("/ws/{room_id}")
async def chat_ws(websocket: WebSocket, room_id: str, nickname: str = Query(default="")):
    await websocket.accept()

    if not nickname or not nickname.strip():
        await websocket.send_text(json.dumps({"error": "nickname is required"}))
        await websocket.close(code=1008)
        return

    nickname = nickname.strip()
    room = get_room(room_id)
    room.connections.add(websocket)
    room.nicknames[websocket] = nickname

    join_msg = {"sender": "system", "text": f"{nickname} joined", "timestamp": now_iso()}
    await broadcast_message(room, join_msg)
    append_history(room, join_msg)

    try:
        while True:
            content = await websocket.receive_text()
            msg = {"sender": nickname, "text": content, "timestamp": now_iso()}
            await broadcast_message(room, msg)
            append_history(room, msg)
    except WebSocketDisconnect:
        room.connections.discard(websocket)
        room.nicknames.pop(websocket, None)
        leave_msg = {"sender": "system", "text": f"{nickname} left", "timestamp": now_iso()}
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
