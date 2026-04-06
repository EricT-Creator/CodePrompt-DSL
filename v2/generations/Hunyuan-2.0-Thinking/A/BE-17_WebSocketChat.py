from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from typing import List
import json

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str, sender: WebSocket):
        for connection in self.active_connections:
            if connection != sender:
                await connection.send_text(message)

    async def send_notification(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(json.dumps({"type": "notification", "message": message}))

manager = ConnectionManager()

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await manager.connect(websocket)
    await manager.send_notification(f"{username} joined the chat")
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = {
                "type": "message",
                "username": username,
                "message": data,
                "timestamp": int(time.time())
            }
            await manager.broadcast(json.dumps(message_data), websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.send_notification(f"{username} left the chat")

if __name__ == "__main__":
    import uvicorn
    import time
    uvicorn.run(app, host="0.0.0.0", port=8000)