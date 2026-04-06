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


def obtain_room(room_id: str) -> Room:
    if room_id not in rooms:
        rooms[room_id] = Room()
    return rooms[room_id]


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


async def fan_out(room: Room, payload: dict) -> None:
    text = json.dumps(payload)
    snapshot = list(room.connections)
    for conn in snapshot:
        try:
            await conn.send_text(text)
        except Exception:
            room.connections.discard(conn)
            room.nicknames.pop(conn, None)


def cap_history(room: Room, entry: dict) -> None:
    room.history.append(entry)
    if len(room.history) > 100:
        room.history = room.history[-100:]


@app.websocket("/ws/{room_id}")
async def websocket_chat(websocket: WebSocket, room_id: str, nickname: str = Query(default="")):
    await websocket.accept()

    if not nickname.strip():
        await websocket.send_text(json.dumps({"error": "nickname is required"}))
        await websocket.close(code=1008)
        return

    name = nickname.strip()
    room = obtain_room(room_id)
    room.connections.add(websocket)
    room.nicknames[websocket] = name

    announcement = {
        "sender": "system",
        "text": f"{name} has joined",
        "timestamp": utc_timestamp(),
    }
    await fan_out(room, announcement)
    cap_history(room, announcement)

    try:
        while True:
            data = await websocket.receive_text()
            message = {
                "sender": name,
                "text": data,
                "timestamp": utc_timestamp(),
            }
            await fan_out(room, message)
            cap_history(room, message)
    except WebSocketDisconnect:
        room.connections.discard(websocket)
        room.nicknames.pop(websocket, None)
        departure = {
            "sender": "system",
            "text": f"{name} has left",
            "timestamp": utc_timestamp(),
        }
        await fan_out(room, departure)
        cap_history(room, departure)
    except Exception:
        room.connections.discard(websocket)
        room.nicknames.pop(websocket, None)
        try:
            await websocket.close()
        except Exception:
            pass


@app.get("/rooms/{room_id}/history")
async def read_history(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    return JSONResponse(content=rooms[room_id].history)


@app.get("/rooms/{room_id}/users")
async def read_users(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    return JSONResponse(content=list(rooms[room_id].nicknames.values()))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
