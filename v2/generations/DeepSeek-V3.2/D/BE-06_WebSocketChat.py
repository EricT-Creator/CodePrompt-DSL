import json
import time
from collections import defaultdict
from typing import Dict, List, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
import uvicorn

# 聊天消息结构
class ChatMessage:
    def __init__(self, username: str, message: str, room: str, timestamp: float = None):
        self.username = username
        self.message = message
        self.room = room
        self.timestamp = timestamp or time.time()
    
    def to_dict(self) -> Dict:
        return {
            "username": self.username,
            "message": self.message,
            "room": self.room,
            "timestamp": self.timestamp,
            "time_formatted": time.strftime("%H:%M:%S", time.localtime(self.timestamp))
        }

# 房间管理器
class ChatRoomManager:
    def __init__(self, max_history: int = 50):
        self.rooms: Dict[str, Set[WebSocket]] = defaultdict(set)
        self.user_nicknames: Dict[WebSocket, str] = {}
        self.message_history: Dict[str, List[ChatMessage]] = defaultdict(list)
        self.max_history = max_history
    
    def add_user_to_room(self, room: str, websocket: WebSocket, nickname: Optional[str] = None):
        """添加用户到房间"""
        self.rooms[room].add(websocket)
        
        if nickname:
            self.user_nicknames[websocket] = nickname
        
        # 发送欢迎消息
        welcome_msg = ChatMessage(
            username="系统",
            message=f"{nickname or '新用户'} 加入了房间",
            room=room
        )
        self.add_message_to_history(welcome_msg)
        
        return nickname
    
    def remove_user_from_room(self, room: str, websocket: WebSocket):
        """从房间移除用户"""
        if room in self.rooms and websocket in self.rooms[room]:
            self.rooms[room].remove(websocket)
            
            nickname = self.user_nicknames.get(websocket, "未知用户")
            goodbye_msg = ChatMessage(
                username="系统",
                message=f"{nickname} 离开了房间",
                room=room
            )
            self.add_message_to_history(goodbye_msg)
            
            # 清理连接
            if websocket in self.user_nicknames:
                del self.user_nicknames[websocket]
    
    def get_nickname(self, websocket: WebSocket) -> Optional[str]:
        """获取用户的昵称"""
        return self.user_nicknames.get(websocket)
    
    def set_nickname(self, websocket: WebSocket, nickname: str):
        """设置用户的昵称"""
        self.user_nicknames[websocket] = nickname
    
    def add_message_to_history(self, message: ChatMessage):
        """添加消息到历史记录"""
        if message.room not in self.message_history:
            self.message_history[message.room] = []
        
        self.message_history[message.room].append(message)
        
        # 保持历史记录不超过最大限制
        if len(self.message_history[message.room]) > self.max_history:
            self.message_history[message.room] = self.message_history[message.room][-self.max_history:]
    
    def get_room_history(self, room: str, limit: int = 50) -> List[Dict]:
        """获取房间消息历史"""
        if room not in self.message_history:
            return []
        
        messages = self.message_history[room]
        return [msg.to_dict() for msg in messages[-limit:]]
    
    def broadcast_to_room(self, room: str, message: Dict, exclude_websocket: Optional[WebSocket] = None):
        """向房间广播消息"""
        if room not in self.rooms:
            return
        
        disconnected = []
        
        for websocket in self.rooms[room]:
            if exclude_websocket and websocket == exclude_websocket:
                continue
            
            try:
                # 使用异步发送
                import asyncio
                asyncio.create_task(websocket.send_json(message))
            except Exception:
                disconnected.append(websocket)
        
        # 清理断开的连接
        for websocket in disconnected:
            self.remove_user_from_room(room, websocket)
    
    def get_room_stats(self) -> Dict[str, Dict]:
        """获取所有房间统计信息"""
        stats = {}
        
        for room, connections in self.rooms.items():
            stats[room] = {
                "user_count": len(connections),
                "active_users": [self.user_nicknames.get(conn, "匿名") for conn in connections],
                "message_count": len(self.message_history.get(room, []))
            }
        
        return stats

# FastAPI应用
app = FastAPI(title="WebSocket聊天服务", description="多房间WebSocket聊天服务")

# 全局房间管理器
room_manager = ChatRoomManager()

# HTML测试页面
html = """
<!DOCTYPE html>
<html>
<head>
    <title>WebSocket聊天测试</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .rooms-panel {
            margin-bottom: 20px;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 5px;
        }
        .chat-room {
            margin-top: 20px;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
        }
        .messages {
            height: 300px;
            overflow-y: auto;
            border: 1px solid #eee;
            padding: 10px;
            margin-bottom: 10px;
            background-color: #fafafa;
        }
        .message {
            margin-bottom: 8px;
            padding: 8px;
            border-radius: 4px;
        }
        .system-message {
            background-color: #e3f2fd;
            color: #1976d2;
        }
        .user-message {
            background-color: #e8f5e8;
        }
        .message-username {
            font-weight: bold;
            color: #333;
        }
        .message-time {
            font-size: 0.8em;
            color: #777;
            margin-left: 10px;
        }
        input, button {
            padding: 10px;
            margin: 5px;
            border-radius: 4px;
            border: 1px solid #ddd;
        }
        button {
            background-color: #007bff;
            color: white;
            cursor: pointer;
        }
        button:hover {
            background-color: #0056b3;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>WebSocket聊天测试</h1>
        
        <div class="rooms-panel">
            <h3>房间列表</h3>
            <div id="rooms-list"></div>
            <button onclick="loadRooms()">刷新房间列表</button>
        </div>
        
        <div class="chat-room">
            <h3>加入聊天室</h3>
            <div>
                <input type="text" id="roomName" placeholder="房间名称 (如: general)" />
                <input type="text" id="nickname" placeholder="昵称" />
                <button onclick="joinRoom()">加入房间</button>
            </div>
            
            <div id="chatArea" style="display:none;">
                <div class="messages" id="messages"></div>
                
                <div>
                    <input type="text" id="messageInput" placeholder="输入消息..." 
                           onkeypress="if(event.keyCode==13) sendMessage()" />
                    <button onclick="sendMessage()">发送</button>
                    <button onclick="leaveRoom()">离开房间</button>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let ws = null;
        let currentRoom = '';
        
        function loadRooms() {
            fetch('/rooms')
                .then(response => response.json())
                .then(data => {
                    const roomsList = document.getElementById('rooms-list');
                    roomsList.innerHTML = '';
                    
                    if (data.rooms && data.rooms.length > 0) {
                        data.rooms.forEach(room => {
                            const roomDiv = document.createElement('div');
                            roomDiv.innerHTML = `
                                <strong>${room.name}</strong>: 
                                ${room.user_count} 人在线
                                <button onclick="joinRoomByName('${room.name}')">加入</button>
                            `;
                            roomsList.appendChild(roomDiv);
                        });
                    } else {
                        roomsList.innerHTML = '<p>暂无活跃房间</p>';
                    }
                });
        }
        
        function joinRoomByName(roomName) {
            document.getElementById('roomName').value = roomName;
            joinRoom();
        }
        
        function joinRoom() {
            const roomName = document.getElementById('roomName').value.trim();
            const nickname = document.getElementById('nickname').value.trim() || '匿名用户';
            
            if (!roomName) {
                alert('请输入房间名称');
                return;
            }
            
            currentRoom = roomName;
            
            // 关闭现有连接
            if (ws) {
                ws.close();
            }
            
            // 创建新的WebSocket连接
            ws = new WebSocket(`ws://localhost:8000/ws/${roomName}`);
            
            ws.onopen = function() {
                console.log('WebSocket连接已建立');
                document.getElementById('chatArea').style.display = 'block';
                
                // 发送昵称
                ws.send(JSON.stringify({
                    type: 'set_nickname',
                    nickname: nickname
                }));
                
                // 获取历史消息
                fetch(`/rooms/${roomName}/history`)
                    .then(response => response.json())
                    .then(data => {
                        const messagesDiv = document.getElementById('messages');
                        messagesDiv.innerHTML = '';
                        
                        data.messages.forEach(msg => {
                            addMessageToDisplay(msg);
                        });
                    });
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                addMessageToDisplay(data);
            };
            
            ws.onclose = function() {
                console.log('WebSocket连接已关闭');
                document.getElementById('chatArea').style.display = 'none';
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket错误:', error);
            };
            
            loadRooms();
        }
        
        function sendMessage() {
            const messageInput = document.getElementById('messageInput');
            const message = messageInput.value.trim();
            
            if (!message) {
                return;
            }
            
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'message',
                    message: message
                }));
                
                messageInput.value = '';
            }
        }
        
        function leaveRoom() {
            if (ws) {
                ws.close();
            }
            
            currentRoom = '';
            document.getElementById('chatArea').style.display = 'none';
            loadRooms();
        }
        
        function addMessageToDisplay(msg) {
            const messagesDiv = document.getElementById('messages');
            
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + 
                (msg.username === '系统' ? 'system-message' : 'user-message');
            
            messageDiv.innerHTML = `
                <span class="message-username">${msg.username}</span>
                <span class="message-time">${msg.time_formatted}</span>
                <div>${msg.message}</div>
            `;
            
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        // 页面加载时获取房间列表
        window.onload = loadRooms;
    </script>
</body>
</html>
"""

@app.get("/")
async def get():
    """返回测试页面"""
    return HTMLResponse(html)

@app.get("/rooms")
async def list_rooms():
    """列出所有活跃房间"""
    stats = room_manager.get_room_stats()
    
    rooms = []
    for room_name, room_stats in stats.items():
        rooms.append({
            "name": room_name,
            "user_count": room_stats["user_count"],
            "active_users": room_stats["active_users"],
            "message_count": room_stats["message_count"]
        })
    
    return {"rooms": rooms}

@app.get("/rooms/{room_name}")
async def get_room_info(room_name: str):
    """获取特定房间信息"""
    stats = room_manager.get_room_stats()
    
    if room_name not in stats:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    return {
        "room": room_name,
        **stats[room_name]
    }

@app.get("/rooms/{room_name}/history")
async def get_room_history(room_name: str, limit: int = 50):
    """获取房间历史消息"""
    history = room_manager.get_room_history(room_name, limit)
    
    return {
        "room": room_name,
        "messages": history
    }

@app.websocket("/ws/{room_name}")
async def websocket_endpoint(websocket: WebSocket, room_name: str):
    """WebSocket聊天端点"""
    await websocket.accept()
    
    nickname = None
    
    try:
        # 等待用户设置昵称
        data = await websocket.receive_json()
        
        if data.get("type") == "set_nickname":
            nickname = data.get("nickname", "匿名用户")
            room_manager.add_user_to_room(room_name, websocket, nickname)
            
            # 发送历史消息
            history = room_manager.get_room_history(room_name, 20)
            for msg in history:
                await websocket.send_json(msg)
        
        # 主消息循环
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "message":
                message_text = data.get("message", "").strip()
                
                if message_text:
                    # 创建新消息
                    chat_message = ChatMessage(
                        username=nickname or "匿名用户",
                        message=message_text,
                        room=room_name
                    )
                    
                    # 添加到历史记录
                    room_manager.add_message_to_history(chat_message)
                    
                    # 广播到房间
                    room_manager.broadcast_to_room(
                        room_name,
                        chat_message.to_dict(),
                        exclude_websocket=websocket
                    )
                    
                    # 发送给自己（回显）
                    await websocket.send_json(chat_message.to_dict())
            
            elif message_type == "ping":
                # 心跳响应
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": time.time()
                })
    
    except WebSocketDisconnect:
        # 用户断开连接
        room_manager.remove_user_from_room(room_name, websocket)
    
    except Exception as e:
        # 其他异常
        print(f"WebSocket错误: {e}")
        room_manager.remove_user_from_room(room_name, websocket)

# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "room_count": len(room_manager.rooms),
        "total_users": sum(len(conns) for conns in room_manager.rooms.values())
    }

# 清理任务（简单实现，生产环境应使用后台任务）
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    print("WebSocket聊天服务已启动")
    print("可用端点:")
    print("  GET /        - 测试页面")
    print("  GET /rooms   - 房间列表")
    print("  GET /health  - 健康检查")
    print("  WS /ws/{room} - WebSocket聊天")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    print("WebSocket聊天服务正在关闭...")

if __name__ == "__main__":
    uvicorn.run(
        "BE_06_WebSocketChat:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )