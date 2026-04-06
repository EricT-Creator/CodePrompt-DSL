import json
import asyncio
from typing import Dict, List, Set
from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Data models
class ChatMessage(BaseModel):
    type: str  # "message", "join", "leave", "nickname"
    room: str
    user: str
    content: str
    timestamp: str

class RoomInfo(BaseModel):
    name: str
    user_count: int
    last_activity: str

class UserInfo(BaseModel):
    nickname: str
    joined_at: str
    room: str

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        # room_name -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # WebSocket -> user info
        self.user_info: Dict[WebSocket, UserInfo] = {}
        # room_name -> list of messages (max 50)
        self.message_history: Dict[str, List[ChatMessage]] = {}
        # room_name -> set of nicknames
        self.room_users: Dict[str, Set[str]] = {}
        
    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        
        if room not in self.active_connections:
            self.active_connections[room] = set()
            self.message_history[room] = []
            self.room_users[room] = set()
            
        self.active_connections[room].add(websocket)
        
        # Generate temporary nickname
        temp_nickname = f"Guest_{uuid4().hex[:6]}"
        user_info = UserInfo(
            nickname=temp_nickname,
            joined_at=datetime.now().isoformat(),
            room=room
        )
        self.user_info[websocket] = user_info
        
        # Send welcome message
        welcome_msg = ChatMessage(
            type="system",
            room=room,
            user="System",
            content=f"Welcome to room '{room}'! Send your nickname as first message.",
            timestamp=datetime.now().isoformat()
        )
        await websocket.send_json(welcome_msg.dict())
        
        return user_info
    
    async def disconnect(self, websocket: WebSocket):
        if websocket in self.user_info:
            user_info = self.user_info[websocket]
            room = user_info.room
            
            # Remove from active connections
            if room in self.active_connections:
                self.active_connections[room].discard(websocket)
                
                # Remove nickname from room
                if room in self.room_users:
                    self.room_users[room].discard(user_info.nickname)
                
                # Send leave message
                leave_msg = ChatMessage(
                    type="leave",
                    room=room,
                    user="System",
                    content=f"{user_info.nickname} has left the chat",
                    timestamp=datetime.now().isoformat()
                )
                await self.broadcast_to_room(room, leave_msg, exclude=websocket)
                
                # Clean up empty rooms
                if not self.active_connections[room]:
                    del self.active_connections[room]
                    del self.message_history[room]
                    del self.room_users[room]
            
            # Remove user info
            del self.user_info[websocket]
    
    async def set_nickname(self, websocket: WebSocket, nickname: str) -> bool:
        if websocket not in self.user_info:
            return False
            
        user_info = self.user_info[websocket]
        room = user_info.room
        
        # Check if nickname is already taken in this room
        if room in self.room_users and nickname in self.room_users[room]:
            return False
        
        # Remove old nickname if exists
        if room in self.room_users and user_info.nickname in self.room_users[room]:
            self.room_users[room].discard(user_info.nickname)
        
        # Add new nickname
        self.room_users[room].add(nickname)
        user_info.nickname = nickname
        
        # Send join message
        join_msg = ChatMessage(
            type="join",
            room=room,
            user="System",
            content=f"{nickname} has joined the chat",
            timestamp=datetime.now().isoformat()
        )
        await self.broadcast_to_room(room, join_msg)
        
        return True
    
    async def send_message(self, websocket: WebSocket, message: str):
        if websocket not in self.user_info:
            return
            
        user_info = self.user_info[websocket]
        room = user_info.room
        
        chat_msg = ChatMessage(
            type="message",
            room=room,
            user=user_info.nickname,
            content=message,
            timestamp=datetime.now().isoformat()
        )
        
        # Add to history (keep last 50 messages)
        if room in self.message_history:
            self.message_history[room].append(chat_msg)
            if len(self.message_history[room]) > 50:
                self.message_history[room] = self.message_history[room][-50:]
        
        # Broadcast to room
        await self.broadcast_to_room(room, chat_msg)
    
    async def broadcast_to_room(self, room: str, message: ChatMessage, exclude: WebSocket = None):
        if room in self.active_connections:
            for connection in self.active_connections[room]:
                if connection != exclude:
                    try:
                        await connection.send_json(message.dict())
                    except:
                        # Remove broken connections
                        await self.disconnect(connection)
    
    def get_room_info(self) -> List[RoomInfo]:
        rooms = []
        for room_name, connections in self.active_connections.items():
            rooms.append(RoomInfo(
                name=room_name,
                user_count=len(connections),
                last_activity=datetime.now().isoformat()
            ))
        return rooms
    
    def get_room_history(self, room: str) -> List[ChatMessage]:
        return self.message_history.get(room, [])
    
    def get_room_users(self, room: str) -> List[str]:
        return list(self.room_users.get(room, []))

# FastAPI app
app = FastAPI(title="WebSocket Chat Server", version="1.0.0")

# Connection manager instance
manager = ConnectionManager()

# HTML for testing
html = """
<!DOCTYPE html>
<html>
<head>
    <title>WebSocket Chat Test</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .container {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .controls {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        input, button {
            padding: 10px;
            font-size: 14px;
        }
        #messages {
            border: 1px solid #ddd;
            height: 400px;
            overflow-y: auto;
            padding: 10px;
            background: #f9f9f9;
        }
        .message {
            margin: 5px 0;
            padding: 8px;
            border-radius: 4px;
            background: white;
        }
        .system {
            background: #e3f2fd;
            color: #1976d2;
        }
        .user {
            background: #f1f8e9;
            color: #33691e;
        }
        .info {
            background: #fff3e0;
            color: #e65100;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>WebSocket Chat Test</h1>
        
        <div class="controls">
            <input id="roomInput" placeholder="Room name" value="general">
            <button onclick="connect()">Connect</button>
            <button onclick="disconnect()" disabled id="disconnectBtn">Disconnect</button>
        </div>
        
        <div class="controls">
            <input id="nicknameInput" placeholder="Nickname">
            <button onclick="setNickname()" disabled id="nicknameBtn">Set Nickname</button>
        </div>
        
        <div class="controls">
            <input id="messageInput" placeholder="Type your message">
            <button onclick="sendMessage()" disabled id="sendBtn">Send</button>
        </div>
        
        <div id="messages"></div>
        
        <div>
            <h3>Active Rooms:</h3>
            <div id="rooms"></div>
        </div>
    </div>
    
    <script>
        let ws = null;
        let currentRoom = '';
        
        function connect() {
            const room = document.getElementById('roomInput').value;
            if (!room) {
                alert('Please enter a room name');
                return;
            }
            
            currentRoom = room;
            ws = new WebSocket(`ws://localhost:8000/ws/${room}`);
            
            ws.onopen = function() {
                console.log('Connected to room:', room);
                document.getElementById('disconnectBtn').disabled = false;
                document.getElementById('nicknameBtn').disabled = false;
                document.getElementById('sendBtn').disabled = false;
                addMessage('System', 'Connected to room: ' + room, 'system');
                fetchRooms();
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                addMessage(data.user, data.content, data.type);
            };
            
            ws.onclose = function() {
                console.log('Disconnected');
                document.getElementById('disconnectBtn').disabled = true;
                document.getElementById('nicknameBtn').disabled = true;
                document.getElementById('sendBtn').disabled = true;
                addMessage('System', 'Disconnected', 'system');
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
                addMessage('System', 'WebSocket error', 'system');
            };
        }
        
        function disconnect() {
            if (ws) {
                ws.close();
                ws = null;
            }
        }
        
        function setNickname() {
            const nickname = document.getElementById('nicknameInput').value;
            if (!nickname) {
                alert('Please enter a nickname');
                return;
            }
            
            if (ws) {
                ws.send(nickname);
            }
        }
        
        function sendMessage() {
            const message = document.getElementById('messageInput').value;
            if (!message) {
                alert('Please enter a message');
                return;
            }
            
            if (ws) {
                ws.send(message);
                document.getElementById('messageInput').value = '';
            }
        }
        
        function addMessage(user, content, type) {
            const messagesDiv = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}`;
            
            const timestamp = new Date().toLocaleTimeString();
            messageDiv.innerHTML = `<strong>[${timestamp}] ${user}:</strong> ${content}`;
            
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        async function fetchRooms() {
            try {
                const response = await fetch('/rooms');
                const rooms = await response.json();
                
                const roomsDiv = document.getElementById('rooms');
                roomsDiv.innerHTML = '';
                
                rooms.forEach(room => {
                    const roomDiv = document.createElement('div');
                    roomDiv.textContent = `${room.name} (${room.user_count} users)`;
                    roomsDiv.appendChild(roomDiv);
                });
            } catch (error) {
                console.error('Error fetching rooms:', error);
            }
        }
        
        // Auto-refresh rooms every 10 seconds
        setInterval(fetchRooms, 10000);
        
        // Send message on Enter key
        document.getElementById('messageInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    </script>
</body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(html)

@app.get("/rooms")
async def get_rooms():
    """Get list of active rooms with user counts."""
    rooms = manager.get_room_info()
    return rooms

@app.get("/rooms/{room_name}/history")
async def get_room_history(room_name: str):
    """Get message history for a specific room."""
    history = manager.get_room_history(room_name)
    return {
        "room": room_name,
        "message_count": len(history),
        "messages": history
    }

@app.get("/rooms/{room_name}/users")
async def get_room_users(room_name: str):
    """Get list of users in a specific room."""
    users = manager.get_room_users(room_name)
    return {
        "room": room_name,
        "user_count": len(users),
        "users": users
    }

@app.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str):
    """WebSocket endpoint for chat rooms."""
    # Connect to room
    user_info = await manager.connect(websocket, room)
    
    try:
        # First message should be nickname
        nickname_set = False
        first_message = await websocket.receive_text()
        
        if await manager.set_nickname(websocket, first_message):
            nickname_set = True
            success_msg = ChatMessage(
                type="system",
                room=room,
                user="System",
                content=f"Nickname set to: {first_message}",
                timestamp=datetime.now().isoformat()
            )
            await websocket.send_json(success_msg.dict())
        else:
            error_msg = ChatMessage(
                type="system",
                room=room,
                user="System",
                content=f"Nickname '{first_message}' is already taken. Please choose another.",
                timestamp=datetime.now().isoformat()
            )
            await websocket.send_json(error_msg.dict())
            
            # Send history
            history = manager.get_room_history(room)
            for msg in history[-10:]:  # Last 10 messages
                await websocket.send_json(msg.dict())
        
        # Handle subsequent messages
        while True:
            data = await websocket.receive_text()
            
            if not nickname_set:
                # Still trying to set nickname
                if await manager.set_nickname(websocket, data):
                    nickname_set = True
                    success_msg = ChatMessage(
                        type="system",
                        room=room,
                        user="System",
                        content=f"Nickname set to: {data}",
                        timestamp=datetime.now().isoformat()
                    )
                    await websocket.send_json(success_msg.dict())
                    
                    # Send history after nickname is set
                    history = manager.get_room_history(room)
                    for msg in history[-10:]:
                        await websocket.send_json(msg.dict())
                else:
                    error_msg = ChatMessage(
                        type="system",
                        room=room,
                        user="System",
                        content=f"Nickname '{data}' is already taken. Please choose another.",
                        timestamp=datetime.now().isoformat()
                    )
                    await websocket.send_json(error_msg.dict())
            else:
                # Regular chat message
                await manager.send_message(websocket, data)
                
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await manager.disconnect(websocket)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    total_connections = sum(len(conns) for conns in manager.active_connections.values())
    total_rooms = len(manager.active_connections)
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "stats": {
            "total_rooms": total_rooms,
            "total_connections": total_connections,
            "total_messages": sum(len(msgs) for msgs in manager.message_history.values()),
            "total_users": len(manager.user_info)
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)