import json
import time
from collections import deque
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI(title="WebSocket Chat")

rooms: dict[str, set[WebSocket]] = {}
room_nicknames: dict[str, dict[WebSocket, str]] = {}
room_history: dict[str, deque[dict[str, Any]]] = {}
HISTORY_LIMIT = 50


def ensure_room(room_name: str) -> None:
    rooms.setdefault(room_name, set())
    room_nicknames.setdefault(room_name, {})
    room_history.setdefault(room_name, deque(maxlen=HISTORY_LIMIT))


def cleanup_room(room_name: str) -> None:
    if rooms.get(room_name):
        return
    rooms.pop(room_name, None)
    room_nicknames.pop(room_name, None)
    room_history.pop(room_name, None)


def append_history(room_name: str, nickname: str, content: str, event: str = "message") -> dict[str, Any]:
    ensure_room(room_name)
    entry = {
        "event": event,
        "room": room_name,
        "nickname": nickname,
        "content": content,
        "timestamp": int(time.time()),
    }
    room_history[room_name].append(entry)
    return entry


async def broadcast(room_name: str, payload: dict[str, Any]) -> None:
    message = json.dumps(payload)
    disconnected: list[WebSocket] = []
    for websocket in list(rooms.get(room_name, set())):
        try:
            await websocket.send_text(message)
        except Exception:
            disconnected.append(websocket)

    for websocket in disconnected:
        rooms.get(room_name, set()).discard(websocket)
        room_nicknames.get(room_name, {}).pop(websocket, None)
    cleanup_room(room_name)


@app.websocket("/ws/{room_name}")
async def websocket_chat(websocket: WebSocket, room_name: str) -> None:
    ensure_room(room_name)
    await websocket.accept()

    nickname = ""
    try:
        first_message = await websocket.receive_text()
        nickname = first_message.strip() or f"guest-{int(time.time() * 1000) % 100000}"
        rooms[room_name].add(websocket)
        room_nicknames[room_name][websocket] = nickname

        await websocket.send_text(
            json.dumps(
                {
                    "event": "history",
                    "room": room_name,
                    "messages": list(room_history[room_name]),
                }
            )
        )

        join_event = append_history(room_name, "system", f"{nickname} joined", event="system")
        await broadcast(room_name, join_event)

        while True:
            content = await websocket.receive_text()
            message = append_history(room_name, nickname, content, event="message")
            await broadcast(room_name, message)
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in rooms.get(room_name, set()):
            rooms[room_name].discard(websocket)
        if websocket in room_nicknames.get(room_name, {}):
            room_nicknames[room_name].pop(websocket, None)
        if nickname:
            leave_event = append_history(room_name, "system", f"{nickname} left", event="system")
            await broadcast(room_name, leave_event)
        cleanup_room(room_name)


@app.get("/rooms")
async def get_rooms():
    items = []
    for room_name in sorted(rooms):
        items.append(
            {
                "room": room_name,
                "connections": len(rooms[room_name]),
                "count": len(rooms[room_name]),
                "history_size": len(room_history.get(room_name, [])),
                "nicknames": sorted(room_nicknames.get(room_name, {}).values()),
            }
        )
    return {"active_rooms": items, "total_rooms": len(items)}


@app.get("/")
async def root():
    return {"service": "websocket-chat", "history_limit": HISTORY_LIMIT}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
