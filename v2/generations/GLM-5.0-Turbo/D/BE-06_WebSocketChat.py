"""
WebSocket聊天服务 - 多房间，内存消息历史
不使用异步队列库，广播遍历连接集合
"""

import json
import time
from typing import Dict, Set
from collections import defaultdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query

app = FastAPI(title="WebSocket Chat Service")

# ===== 数据结构 =====

class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, Set[WebSocket]] = defaultdict(set)
        self.histories: Dict[str, list] = defaultdict(list)
        self.nicknames: Dict[WebSocket, str] = {}
        self.connection_times: Dict[WebSocket, float] = {}

    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        self.rooms[room].add(websocket)
        self.connection_times[websocket] = time.time()

    def disconnect(self, websocket: WebSocket, room: str):
        self.rooms[room].discard(websocket)
        self.connection_times.pop(websocket, None)
        self.nicknames.pop(websocket, None)
        if not self.rooms[room]:
            del self.rooms[room]
            if room in self.histories:
                del self.histories[room]

    def set_nickname(self, websocket: WebSocket, nickname: str):
        self.nicknames[websocket] = nickname

    def get_nickname(self, websocket: WebSocket) -> str:
        return self.nicknames.get(websocket, "匿名")

    async def broadcast(self, room: str, message: dict, exclude: WebSocket = None):
        disconnected = []
        for conn in self.rooms.get(room, set()):
            if conn == exclude:
                continue
            try:
                await conn.send_json(message)
            except Exception:
                disconnected.append(conn)
        for conn in disconnected:
            self.disconnect(conn, room)

    def add_history(self, room: str, message: dict):
        history = self.histories[room]
        history.append(message)
        if len(history) > 50:
            self.histories[room] = history[-50:]

    def get_history(self, room: str) -> list:
        return list(self.histories.get(room, []))

    def get_active_rooms(self) -> list:
        result = []
        for room, connections in self.rooms.items():
            if connections:
                result.append({
                    "room": room,
                    "members": len(connections),
                })
        return sorted(result, key=lambda x: x["room"])

manager = ConnectionManager()

# ===== HTTP路由 =====

@app.get("/rooms")
async def list_rooms():
    return {"rooms": manager.get_active_rooms()}

# ===== WebSocket路由 =====

@app.websocket("/ws/chat/{room}")
async def websocket_chat(websocket: WebSocket, room: str):
    await manager.connect(websocket, room)
    nickname_set = False

    try:
        history = manager.get_history(room)
        if history:
            await websocket.send_json({
                "type": "history",
                "room": room,
                "messages": history,
            })

        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "detail": "消息格式无效，请发送JSON",
                })
                continue

            if not nickname_set:
                nickname = msg.get("nickname", msg.get("text", "匿名"))[:20]
                nickname_set = True
                manager.set_nickname(websocket, nickname)
                welcome = {
                    "type": "system",
                    "text": f"{nickname} 加入了房间",
                    "room": room,
                    "timestamp": time.time(),
                }
                manager.add_history(room, welcome)
                await manager.broadcast(room, welcome)
                continue

            nickname = manager.get_nickname(websocket)
            chat_msg = {
                "type": "message",
                "nickname": nickname,
                "text": msg.get("text", "")[:500],
                "room": room,
                "timestamp": time.time(),
            }
            manager.add_history(room, chat_msg)
            await manager.broadcast(room, chat_msg)

    except WebSocketDisconnect:
        if nickname_set:
            nickname = manager.get_nickname(websocket)
            leave_msg = {
                "type": "system",
                "text": f"{nickname} 离开了房间",
                "room": room,
                "timestamp": time.time(),
            }
            manager.add_history(room, leave_msg)
            await manager.broadcast(room, leave_msg, exclude=websocket)
    except Exception:
        pass
    finally:
        manager.disconnect(websocket, room)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
