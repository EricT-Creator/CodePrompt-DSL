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


def find_or_create_room(room_id: str) -> Room:
    if room_id not in rooms:
        rooms[room_id] = Room()
    return rooms[room_id]


def current_time() -> str:
    return datetime.now(timezone.utc).isoformat()


async def broadcast_to_room(room: Room, message: dict) -> None:
    serialized = json.dumps(message)
    targets = list(room.connections)
    for target in targets:
        try:
            await target.send_text(serialized)
        except Exception:
            room.connections.discard(target)
            room.nicknames.pop(target, None)


def log_message(room: Room, message: dict) -> None:
    room.history.append(message)
    if len(room.history) > 100:
        room.history = room.history[-100:]


@app.websocket("/ws/{room_id}")
async def websocket_handler(websocket: WebSocket, room_id: str, nickname: str = Query(default="")):
    await websocket.accept()

    if not nickname or not nickname.strip():
        await websocket.send_text(json.dumps({"error": "nickname is required"}))
        await websocket.close(code=1008)
        return

    clean_nick = nickname.strip()
    room = find_or_create_room(room_id)
    room.connections.add(websocket)
    room.nicknames[websocket] = clean_nick

    entry_notice = {
        "sender": "system",
        "text": f"{clean_nick} joined the room",
        "timestamp": current_time(),
    }
    await broadcast_to_room(room, entry_notice)
    log_message(room, entry_notice)

    try:
        while True:
            incoming = await websocket.receive_text()
            chat_msg = {
                "sender": clean_nick,
                "text": incoming,
                "timestamp": current_time(),
            }
            await broadcast_to_room(room, chat_msg)
            log_message(room, chat_msg)
    except WebSocketDisconnect:
        room.connections.discard(websocket)
        room.nicknames.pop(websocket, None)
        exit_notice = {
            "sender": "system",
            "text": f"{clean_nick} left the room",
            "timestamp": current_time(),
        }
        await broadcast_to_room(room, exit_notice)
        log_message(room, exit_notice)
    except Exception:
        room.connections.discard(websocket)
        room.nicknames.pop(websocket, None)
        try:
            await websocket.close()
        except Exception:
            pass


@app.get("/rooms/{room_id}/history")
async def fetch_history(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    return JSONResponse(content=rooms[room_id].history)


@app.get("/rooms/{room_id}/users")
async def fetch_users(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    return JSONResponse(content=list(rooms[room_id].nicknames.values()))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
