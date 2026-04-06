import json
from typing import Dict, List, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

app = FastAPI(title="WebSocket Chat Server")

class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, Set[WebSocket]] = {}
        self.nicknames: Dict[WebSocket, str] = {}
        self.history: Dict[str, List[Dict]] = {}
        self.max_history = 50

    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        
        if room not in self.rooms:
            self.rooms[room] = set()
            self.history[room] = []
        
        self.rooms[room].add(websocket)

    def disconnect(self, websocket: WebSocket, room: str):
        if room in self.rooms:
            self.rooms[room].discard(websocket)
            if len(self.rooms[room]) == 0:
                del self.rooms[room]
                del self.history[room]
        
        if websocket in self.nicknames:
            del self.nicknames[websocket]

    def set_nickname(self, websocket: WebSocket, nickname: str):
        self.nicknames[websocket] = nickname

    def get_nickname(self, websocket: WebSocket) -> str:
        return self.nicknames.get(websocket, "Anonymous")

    async def broadcast(self, room: str, message: Dict, exclude: WebSocket = None):
        if room not in self.rooms:
            return
        
        message_json = json.dumps(message)
        disconnected = []
        
        for connection in self.rooms[room]:
            if connection != exclude:
                try:
                    await connection.send_text(message_json)
                except Exception:
                    disconnected.append(connection)
        
        for conn in disconnected:
            self.rooms[room].discard(conn)

    def add_to_history(self, room: str, message: Dict):
        if room not in self.history:
            self.history[room] = []
        
        self.history[room].append(message)
        if len(self.history[room]) > self.max_history:
            self.history[room].pop(0)

    def get_history(self, room: str) -> List[Dict]:
        return self.history.get(room, []).copy()

    def get_room_stats(self) -> Dict[str, Dict]:
        return {
            room: {
                "user_count": len(connections),
                "message_count": len(self.history.get(room, []))
            }
            for room, connections in self.rooms.items()
        }

manager = RoomManager()

@app.get("/")
async def root():
    return {"message": "WebSocket Chat Server", "endpoints": ["/ws/{room}", "/rooms"]}

@app.get("/rooms")
async def get_rooms():
    stats = manager.get_room_stats()
    return JSONResponse(content={
        "rooms": stats,
        "total_rooms": len(stats)
    })

@app.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str):
    await manager.connect(websocket, room)
    nickname_set = False
    
    try:
        history = manager.get_history(room)
        if history:
            await websocket.send_text(json.dumps({
                "type": "history",
                "messages": history
            }))
        
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON"
                }))
                continue
            
            if not nickname_set:
                nickname = message.get("nickname", "Anonymous")
                manager.set_nickname(websocket, nickname)
                nickname_set = True
                
                join_message = {
                    "type": "system",
                    "message": f"{nickname} joined the room",
                    "timestamp": json.dumps({}).join([]) or str(__import__('time').time())
                }
                join_message["timestamp"] = str(__import__('time').time())
                
                await manager.broadcast(room, {
                    "type": "system",
                    "message": f"{nickname} joined the room",
                    "timestamp": __import__('time').time()
                })
                continue
            
            msg_type = message.get("type", "message")
            
            if msg_type == "message":
                nickname = manager.get_nickname(websocket)
                chat_message = {
                    "type": "message",
                    "nickname": nickname,
                    "message": message.get("message", ""),
                    "timestamp": __import__('time').time()
                }
                
                manager.add_to_history(room, chat_message)
                await manager.broadcast(room, chat_message)
            
            elif msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    
    except WebSocketDisconnect:
        if nickname_set:
            nickname = manager.get_nickname(websocket)
            await manager.broadcast(room, {
                "type": "system",
                "message": f"{nickname} left the room",
                "timestamp": __import__('time').time()
            })
        manager.disconnect(websocket, room)
    
    except Exception as e:
        print(f"Error: {e}")
        manager.disconnect(websocket, room)

if __name__ == "__main__":
    import uvicorn
    import time
    uvicorn.run(app, host="0.0.0.0", port=8000)
