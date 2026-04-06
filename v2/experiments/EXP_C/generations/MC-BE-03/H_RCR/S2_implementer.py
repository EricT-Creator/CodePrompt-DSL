from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Dict, Set, Tuple, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel


class ConnectionManager:
    def __init__(self) -> None:
        self.rooms: Dict[str, Set[Tuple[str, WebSocket]]] = {}
        self.history: Dict[str, List[Dict]] = {}
        self.MAX_HISTORY = 100

    def connect(self, room_id: str, nickname: str, ws: WebSocket) -> bool:
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
            self.history[room_id] = []

        for existing_nick, _ in self.rooms[room_id]:
            if existing_nick == nickname:
                return False

        self.rooms[room_id].add((nickname, ws))
        return True

    def disconnect(self, room_id: str, nickname: str) -> None:
        if room_id not in self.rooms:
            return

        conn_to_remove = None
        for nick, ws in self.rooms[room_id]:
            if nick == nickname:
                conn_to_remove = (nick, ws)
                break

        if conn_to_remove:
            self.rooms[room_id].discard(conn_to_remove)

        if len(self.rooms[room_id]) == 0:
            del self.rooms[room_id]
            del self.history[room_id]

    async def broadcast(self, room_id: str, message: Dict) -> None:
        if room_id not in self.rooms:
            return

        dead_connections: List[Tuple[str, WebSocket]] = []

        for nickname, ws in self.rooms[room_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead_connections.append((nickname, ws))

        for conn in dead_connections:
            self.rooms[room_id].discard(conn)

    def store_message(self, room_id: str, message: Dict) -> None:
        if room_id not in self.history:
            self.history[room_id] = []

        self.history[room_id].append(message)

        if len(self.history[room_id]) > self.MAX_HISTORY:
            self.history[room_id] = self.history[room_id][-self.MAX_HISTORY:]

    def get_history(self, room_id: str) -> List[Dict]:
        return self.history.get(room_id, []).copy()

    def get_users(self, room_id: str) -> List[str]:
        if room_id not in self.rooms:
            return []
        return [nick for nick, _ in self.rooms[room_id]]


def build_message(nickname: str, text: str) -> Dict:
    return {
        "type": "message",
        "nickname": nickname,
        "text": text,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def system_message(text: str) -> Dict:
    return {
        "type": "system",
        "nickname": "system",
        "text": text,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


class RoomUsersResponse(BaseModel):
    room_id: str
    users: List[str]
    count: int


app = FastAPI(title="WebSocket Chat Server")
manager = ConnectionManager()


@app.websocket("/ws/{room_id}/{nickname}")
async def websocket_endpoint(ws: WebSocket, room_id: str, nickname: str) -> None:
    await ws.accept()

    if not manager.connect(room_id, nickname, ws):
        await ws.close(code=4001, reason="Nickname already taken")
        return

    try:
        for msg in manager.get_history(room_id):
            await ws.send_json(msg)

        await manager.broadcast(room_id, system_message(f"{nickname} joined"))

        while True:
            try:
                data = await ws.receive_json()
                text = data.get("text", "")
                if text:
                    message = build_message(nickname, text)
                    manager.store_message(room_id, message)
                    await manager.broadcast(room_id, message)
            except json.JSONDecodeError:
                continue

    except WebSocketDisconnect:
        manager.disconnect(room_id, nickname)
        await manager.broadcast(room_id, system_message(f"{nickname} left"))


@app.get("/rooms/{room_id}/users", response_model=RoomUsersResponse)
async def get_room_users(room_id: str) -> RoomUsersResponse:
    users = manager.get_users(room_id)
    return RoomUsersResponse(
        room_id=room_id,
        users=users,
        count=len(users)
    )
