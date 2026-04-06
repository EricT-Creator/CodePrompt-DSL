#!/usr/bin/env python3
"""
WebSocket聊天服务器 - 使用FastAPI实现
支持多房间、昵称、历史消息和房间统计
"""

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Set, Optional, Any
from collections import defaultdict, deque

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, validator


# 数据模型
class ChatMessage(BaseModel):
    type: str  # "message", "join", "leave", "system", "nickname"
    room: str
    content: str
    sender: Optional[str] = None
    timestamp: Optional[float] = None
    nickname: Optional[str] = None
    
    @validator('timestamp', pre=True, always=True)
    def set_timestamp(cls, v):
        return v or time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "room": self.room,
            "content": self.content,
            "sender": self.sender,
            "timestamp": self.timestamp,
            "formatted_time": datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S"),
            "nickname": self.nickname
        }


class RoomInfo(BaseModel):
    name: str
    user_count: int
    message_count: int
    last_activity: float
    created_at: float


class UserInfo(BaseModel):
    nickname: str
    joined_at: float
    last_active: float
    room: str


# 连接管理器
class ConnectionManager:
    def __init__(self, max_history_per_room: int = 50):
        # 房间到连接的映射
        self.rooms: Dict[str, Set[WebSocket]] = defaultdict(set)
        
        # 连接信息
        self.connections: Dict[WebSocket, Dict[str, Any]] = {}
        
        # 房间历史消息
        self.history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history_per_room))
        
        # 房间统计
        self.room_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "created_at": time.time(),
            "message_count": 0,
            "last_activity": time.time(),
            "user_nicknames": set()
        })
        
        # 用户昵称映射
        self.nicknames: Dict[WebSocket, str] = {}
        
        # 锁，用于并发控制
        self.lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, room: str):
        """连接WebSocket到指定房间"""
        await websocket.accept()
        
        async with self.lock:
            self.rooms[room].add(websocket)
            self.connections[websocket] = {
                "room": room,
                "connected_at": time.time(),
                "last_active": time.time(),
                "nickname": None
            }
            
            # 更新房间统计
            self.room_stats[room]["last_activity"] = time.time()
            
        # 发送欢迎消息
        welcome_msg = ChatMessage(
            type="system",
            room=room,
            content=f"欢迎来到聊天室 '{room}'！请发送消息设置昵称。",
            sender="system"
        )
        await websocket.send_json(welcome_msg.to_dict())
        
        # 发送房间历史
        if room in self.history:
            history_msgs = list(self.history[room])
            await websocket.send_json({
                "type": "history",
                "room": room,
                "messages": history_msgs,
                "count": len(history_msgs)
            })
        
        return True
    
    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        async with self.lock:
            if websocket in self.connections:
                room = self.connections[websocket]["room"]
                nickname = self.connections[websocket]["nickname"]
                
                # 从房间移除
                if websocket in self.rooms[room]:
                    self.rooms[room].remove(websocket)
                
                # 从昵称映射中移除
                if websocket in self.nicknames:
                    del self.nicknames[websocket]
                
                # 从连接信息中移除
                del self.connections[websocket]
                
                # 发送离开消息
                if nickname:
                    leave_msg = ChatMessage(
                        type="leave",
                        room=room,
                        content=f"{nickname} 离开了聊天室",
                        sender=nickname
                    )
                    
                    # 添加到历史
                    self.history[room].append(leave_msg.to_dict())
                    self.room_stats[room]["message_count"] += 1
                    self.room_stats[room]["user_nicknames"].discard(nickname)
                    
                    # 广播离开消息（异步）
                    asyncio.create_task(self.broadcast(leave_msg, room, exclude=websocket))
    
    async def receive_message(self, websocket: WebSocket) -> Optional[Dict]:
        """接收消息"""
        try:
            data = await websocket.receive_json()
            
            # 更新活跃时间
            if websocket in self.connections:
                self.connections[websocket]["last_active"] = time.time()
            
            return data
        except Exception as e:
            print(f"接收消息错误: {e}")
            return None
    
    async def send_message(self, websocket: WebSocket, message: Dict):
        """发送消息到指定WebSocket"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"发送消息错误: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: ChatMessage, room: str, exclude: Optional[WebSocket] = None):
        """广播消息到房间所有连接"""
        message_dict = message.to_dict()
        
        # 添加到历史记录
        if message.type in ["message", "join", "leave", "system"]:
            async with self.lock:
                self.history[room].append(message_dict)
                self.room_stats[room]["message_count"] += 1
                self.room_stats[room]["last_activity"] = time.time()
        
        # 广播到所有连接
        tasks = []
        for websocket in list(self.rooms[room]):
            if websocket != exclude:
                tasks.append(self.send_message(websocket, message_dict))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def process_chat_message(self, websocket: WebSocket, data: Dict) -> bool:
        """处理聊天消息"""
        if websocket not in self.connections:
            return False
        
        room = self.connections[websocket]["room"]
        current_nickname = self.connections[websocket].get("nickname")
        
        message_type = data.get("type", "message")
        content = data.get("content", "").strip()
        
        if not content:
            return False
        
        # 处理昵称设置
        if not current_nickname:
            nickname = content[:20]  # 限制昵称长度
            self.connections[websocket]["nickname"] = nickname
            self.nicknames[websocket] = nickname
            
            # 添加到房间昵称集合
            async with self.lock:
                self.room_stats[room]["user_nicknames"].add(nickname)
            
            # 发送加入消息
            join_msg = ChatMessage(
                type="join",
                room=room,
                content=f"{nickname} 加入了聊天室",
                sender=nickname
            )
            await self.broadcast(join_msg, room)
            
            # 发送昵称确认
            confirm_msg = ChatMessage(
                type="system",
                room=room,
                content=f"您的昵称已设置为: {nickname}",
                sender="system"
            )
            await self.send_message(websocket, confirm_msg.to_dict())
            
            return True
        
        # 处理普通消息
        if message_type == "message":
            chat_msg = ChatMessage(
                type="message",
                room=room,
                content=content,
                sender=current_nickname,
                nickname=current_nickname
            )
            await self.broadcast(chat_msg, room)
            return True
        
        return False
    
    def get_room_info(self, room: str) -> Optional[RoomInfo]:
        """获取房间信息"""
        if room not in self.room_stats:
            return None
        
        stats = self.room_stats[room]
        return RoomInfo(
            name=room,
            user_count=len(self.rooms[room]),
            message_count=stats["message_count"],
            last_activity=stats["last_activity"],
            created_at=stats["created_at"]
        )
    
    def get_all_rooms(self) -> List[RoomInfo]:
        """获取所有房间信息"""
        rooms = []
        for room_name in self.rooms.keys():
            room_info = self.get_room_info(room_name)
            if room_info:
                rooms.append(room_info)
        return rooms
    
    def get_room_users(self, room: str) -> List[UserInfo]:
        """获取房间用户信息"""
        users = []
        for websocket in self.rooms.get(room, []):
            if websocket in self.connections:
                conn_info = self.connections[websocket]
                if conn_info["nickname"]:
                    users.append(UserInfo(
                        nickname=conn_info["nickname"],
                        joined_at=conn_info["connected_at"],
                        last_active=conn_info["last_active"],
                        room=room
                    ))
        return users
    
    def cleanup_inactive_rooms(self, max_inactive_seconds: int = 3600):
        """清理不活跃的房间"""
        current_time = time.time()
        rooms_to_remove = []
        
        for room_name, stats in self.room_stats.items():
            inactive_time = current_time - stats["last_activity"]
            if inactive_time > max_inactive_seconds and len(self.rooms[room_name]) == 0:
                rooms_to_remove.append(room_name)
        
        for room_name in rooms_to_remove:
            del self.rooms[room_name]
            del self.history[room_name]
            del self.room_stats[room_name]
        
        return len(rooms_to_remove)


# 创建应用
app = FastAPI(
    title="WebSocket聊天服务器",
    description="支持多房间的实时WebSocket聊天服务器",
    version="1.0.0"
)

# 连接管理器实例
manager = ConnectionManager(max_history_per_room=50)

# HTML前端页面
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>WebSocket聊天室</title>
    <meta charset="utf-8">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 20px;
            height: 90vh;
        }
        
        .sidebar {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            display: flex;
            flex-direction: column;
        }
        
        .chat-container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            display: flex;
            flex-direction: column;
        }
        
        h1 {
            color: #333;
            margin-bottom: 20px;
            text-align: center;
            font-size: 24px;
        }
        
        h2 {
            color: #444;
            margin-bottom: 15px;
            font-size: 18px;
        }
        
        .room-selector {
            margin-bottom: 20px;
        }
        
        .room-input {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
        }
        
        input {
            flex: 1;
            padding: 10px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        button {
            padding: 10px 20px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
        }
        
        button:hover {
            background: #5a67d8;
            transform: translateY(-2px);
        }
        
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        
        .room-list {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
            max-height: 200px;
            overflow-y: auto;
        }
        
        .room-item {
            padding: 8px 12px;
            margin-bottom: 8px;
            background: white;
            border-radius: 6px;
            border: 1px solid #e0e0e0;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .room-item:hover {
            border-color: #667eea;
            background: #f0f4ff;
        }
        
        .room-item.active {
            border-color: #667eea;
            background: #e0e7ff;
            font-weight: 600;
        }
        
        .user-list {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            flex: 1;
            overflow-y: auto;
        }
        
        .user-item {
            padding: 8px 12px;
            margin-bottom: 6px;
            background: white;
            border-radius: 6px;
            border-left: 4px solid #667eea;
            font-size: 14px;
        }
        
        .chat-messages {
            flex: 1;
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        
        .message {
            padding: 12px 15px;
            border-radius: 10px;
            max-width: 80%;
            word-wrap: break-word;
            animation: fadeIn 0.3s ease;
        }
        
        .message.own {
            align-self: flex-end;
            background: #667eea;
            color: white;
            border-bottom-right-radius: 0;
        }
        
        .message.other {
            align-self: flex-start;
            background: white;
            color: #333;
            border: 1px solid #e0e0e0;
            border-bottom-left-radius: 0;
        }
        
        .message.system {
            align-self: center;
            background: #f0f0f0;
            color: #666;
            font-style: italic;
            max-width: 90%;
            text-align: center;
        }
        
        .message.join {
            background: #e8f5e9;
            color: #2e7d32;
            border: 1px solid #c8e6c9;
        }
        
        .message.leave {
            background: #ffebee;
            color: #c62828;
            border: 1px solid #ffcdd2;
        }
        
        .message-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
            font-size: 12px;
            opacity: 0.8;
        }
        
        .message-content {
            line-height: 1.4;
        }
        
        .chat-input {
            display: flex;
            gap: 10px;
        }
        
        .chat-input input {
            flex: 1;
        }
        
        .status {
            padding: 10px;
            background: #f8f9fa;
            border-radius: 8px;
            margin-top: 10px;
            text-align: center;
            font-size: 13px;
            color: #666;
        }
        
        .connected {
            color: #4caf50;
        }
        
        .disconnected {
            color: #f44336;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        @media (max-width: 768px) {
            .container {
                grid-template-columns: 1fr;
                height: auto;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <h1>💬 WebSocket聊天室</h1>
            
            <div class="room-selector">
                <h2>选择房间</h2>
                <div class="room-input">
                    <input type="text" id="roomInput" placeholder="输入房间名称" value="general">
                    <button id="connectBtn">连接</button>
                </div>
                
                <div class="room-list" id="roomList">
                    <!-- 房间列表将动态加载 -->
                </div>
            </div>
            
            <div class="user-section">
                <h2>在线用户</h2>
                <div class="user-list" id="userList">
                    <!-- 用户列表将动态更新 -->
                </div>
            </div>
            
            <div class="status" id="status">
                <span id="statusText">未连接</span>
            </div>
        </div>
        
        <div class="chat-container">
            <h2 id="roomTitle">聊天室</h2>
            
            <div class="chat-messages" id="chatMessages">
                <!-- 消息将动态添加 -->
                <div class="message system">
                    欢迎使用WebSocket聊天室！连接房间后开始聊天。
                </div>
            </div>
            
            <div class="chat-input">
                <input type="text" id="messageInput" placeholder="输入消息..." disabled>
                <button id="sendBtn" disabled>发送</button>
            </div>
        </div>
    </div>
    
    <script>
        let ws = null;
        let currentRoom = "";
        let currentNickname = "";
        let isSettingNickname = false;
        
        // DOM元素
        const roomInput = document.getElementById('roomInput');
        const connectBtn = document.getElementById('connectBtn');
        const roomList = document.getElementById('roomList');
        const userList = document.getElementById('userList');
        const statusText = document.getElementById('statusText');
        const roomTitle = document.getElementById('roomTitle');
        const chatMessages = document.getElementById('chatMessages');
        const messageInput = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');
        
        // 连接WebSocket
        async function connectWebSocket(room) {
            if (ws) {
                ws.close();
            }
            
            try {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws/${room}`;
                
                ws = new WebSocket(wsUrl);
                
                ws.onopen = () => {
                    updateStatus('connected');
                    roomTitle.textContent = `聊天室: ${room}`;
                    currentRoom = room;
                    
                    messageInput.placeholder = "发送消息设置您的昵称...";
                    messageInput.disabled = false;
                    sendBtn.disabled = false;
                    messageInput.focus();
                    
                    isSettingNickname = true;
                    loadRooms();
                };
                
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    handleMessage(data);
                };
                
                ws.onclose = () => {
                    updateStatus('disconnected');
                    currentRoom = "";
                    currentNickname = "";
                    
                    messageInput.disabled = true;
                    sendBtn.disabled = true;
                    messageInput.placeholder = "连接房间后开始聊天...";
                    
                    chatMessages.innerHTML = '<div class="message system">连接已断开</div>';
                };
                
                ws.onerror = (error) => {
                    console.error('WebSocket错误:', error);
                    updateStatus('error');
                    alert('连接失败，请重试');
                };
                
            } catch (error) {
                console.error('连接错误:', error);
                alert('连接失败: ' + error.message);
            }
        }
        
        // 处理接收到的消息
        function handleMessage(data) {
            if (data.type === 'history') {
                // 清空消息列表
                chatMessages.innerHTML = '';
                
                // 显示历史消息
                data.messages.forEach(msg => {
                    addMessageToChat(msg);
                });
                
                // 显示历史消息计数
                const historyMsg = document.createElement('div');
                historyMsg.className = 'message system';
                historyMsg.textContent = `已加载 ${data.count} 条历史消息`;
                chatMessages.appendChild(historyMsg);
                
                return;
            }
            
            if (data.type === 'system') {
                if (data.content.includes('昵称已设置为')) {
                    currentNickname = data.content.split(': ')[1];
                    isSettingNickname = false;
                    messageInput.placeholder = "输入消息...";
                }
            }
            
            addMessageToChat(data);
        }
        
        // 添加消息到聊天界面
        function addMessageToChat(data) {
            const messageDiv = document.createElement('div');
            
            let messageClass = 'message ';
            if (data.type === 'system') {
                messageClass += 'system';
            } else if (data.type === 'join') {
                messageClass += 'join';
            } else if (data.type === 'leave') {
                messageClass += 'leave';
            } else if (data.sender === currentNickname) {
                messageClass += 'own';
            } else {
                messageClass += 'other';
            }
            
            messageDiv.className = messageClass;
            
            const headerDiv = document.createElement('div');
            headerDiv.className = 'message-header';
            
            const senderSpan = document.createElement('span');
            senderSpan.textContent = data.sender || data.nickname || '系统';
            
            const timeSpan = document.createElement('span');
            timeSpan.textContent = data.formatted_time || new Date().toLocaleTimeString();
            
            headerDiv.appendChild(senderSpan);
            headerDiv.appendChild(timeSpan);
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            contentDiv.textContent = data.content;
            
            messageDiv.appendChild(headerDiv);
            messageDiv.appendChild(contentDiv);
            
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        // 发送消息
        function sendMessage() {
            const content = messageInput.value.trim();
            if (!content || !ws || ws.readyState !== WebSocket.OPEN) {
                return;
            }
            
            const message = {
                type: 'message',
                content: content
            };
            
            ws.send(JSON.stringify(message));
            messageInput.value = '';
            messageInput.focus();
        }
        
        // 更新连接状态
        function updateStatus(status) {
            statusText.textContent = {
                'connected': '🟢 已连接',
                'disconnected': '🔴 未连接',
                'error': '⚠️ 连接错误'
            }[status] || '未知状态';
            
            statusText.className = status;
        }
        
        // 加载房间列表
        async function loadRooms() {
            try {
                const response = await fetch('/rooms');
                const data = await response.json();
                
                roomList.innerHTML = '';
                data.rooms.forEach(room => {
                    const roomItem = document.createElement('div');
                    roomItem.className = 'room-item' + (room.name === currentRoom ? ' active' : '');
                    roomItem.textContent = `${room.name} (${room.user_count}人在线)`;
                    
                    roomItem.onclick = () => {
                        if (room.name !== currentRoom) {
                            roomInput.value = room.name;
                            connectBtn.click();
                        }
                    };
                    
                    roomList.appendChild(roomItem);
                });
                
            } catch (error) {
                console.error('加载房间列表错误:', error);
            }
        }
        
        // 加载用户列表
        async function loadUsers(room) {
            try {
                const response = await fetch(`/rooms/${room}/users`);
                const data = await response.json();
                
                userList.innerHTML = '';
                data.users.forEach(user => {
                    const userItem = document.createElement('div');
                    userItem.className = 'user-item';
                    
                    const activeTime = Math.floor((Date.now()/1000 - user.last_active) / 60);
                    const activeText = activeTime < 1 ? '刚刚活跃' : `${activeTime}分钟前活跃`;
                    
                    userItem.textContent = `${user.nickname} (${activeText})`;
                    userList.appendChild(userItem);
                });
                
            } catch (error) {
                console.error('加载用户列表错误:', error);
            }
        }
        
        // 事件监听
        connectBtn.onclick = () => {
            const room = roomInput.value.trim();
            if (room) {
                connectWebSocket(room);
            }
        };
        
        sendBtn.onclick = sendMessage;
        
        messageInput.onkeypress = (event) => {
            if (event.key === 'Enter') {
                sendMessage();
            }
        };
        
        // 定时加载房间和用户信息
        setInterval(() => {
            if (currentRoom) {
                loadRooms();
                loadUsers(currentRoom);
            }
        }, 5000);
        
        // 初始加载房间列表
        loadRooms();
        
        // 页面卸载时关闭连接
        window.onbeforeunload = () => {
            if (ws) {
                ws.close();
            }
        };
    </script>
</body>
</html>
"""


# HTTP路由
@app.get("/", response_class=HTMLResponse)
async def get_html_page():
    """返回聊天界面HTML页面"""
    return HTMLResponse(content=HTML_PAGE)


@app.get("/rooms", response_model=Dict[str, Any])
async def get_rooms():
    """获取所有房间信息"""
    rooms = manager.get_all_rooms()
    return {
        "rooms": [room.dict() for room in rooms],
        "total_rooms": len(rooms),
        "total_connections": sum(len(conns) for conns in manager.rooms.values()),
        "timestamp": time.time()
    }


@app.get("/rooms/{room_name}", response_model=Dict[str, Any])
async def get_room_info(room_name: str):
    """获取特定房间信息"""
    room_info = manager.get_room_info(room_name)
    if not room_info:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    users = manager.get_room_users(room_name)
    history_count = len(manager.history.get(room_name, []))
    
    return {
        "room": room_info.dict(),
        "users": [user.dict() for user in users],
        "history_count": history_count,
        "is_active": len(manager.rooms.get(room_name, [])) > 0
    }


@app.get("/rooms/{room_name}/users", response_model=Dict[str, Any])
async def get_room_users(room_name: str):
    """获取房间用户列表"""
    users = manager.get_room_users(room_name)
    return {
        "room": room_name,
        "users": [user.dict() for user in users],
        "user_count": len(users),
        "timestamp": time.time()
    }


@app.get("/rooms/{room_name}/history")
async def get_room_history(room_name: str, limit: int = Query(20, ge=1, le=100)):
    """获取房间历史消息"""
    if room_name not in manager.history:
        raise HTTPException(status_code=404, detail="房间不存在或没有历史消息")
    
    history = list(manager.history[room_name])[-limit:]
    return {
        "room": room_name,
        "messages": history,
        "count": len(history),
        "has_more": len(manager.history[room_name]) > limit
    }


@app.delete("/rooms/{room_name}")
async def cleanup_room(room_name: str):
    """清理房间（仅当没有用户时）"""
    if room_name in manager.rooms and len(manager.rooms[room_name]) > 0:
        raise HTTPException(status_code=400, detail="房间仍有用户，无法清理")
    
    if room_name in manager.rooms:
        del manager.rooms[room_name]
    if room_name in manager.history:
        del manager.history[room_name]
    if room_name in manager.room_stats:
        del manager.room_stats[room_name]
    
    return {"message": f"房间 '{room_name}' 已清理", "success": True}


# WebSocket路由
@app.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str):
    """WebSocket聊天端点"""
    # 连接
    await manager.connect(websocket, room)
    
    try:
        while True:
            # 接收消息
            data = await manager.receive_message(websocket)
            if not data:
                continue
            
            # 处理消息
            success = await manager.process_chat_message(websocket, data)
            if not success:
                error_msg = ChatMessage(
                    type="system",
                    room=room,
                    content="消息格式错误或处理失败",
                    sender="system"
                )
                await manager.send_message(websocket, error_msg.to_dict())
                
    except WebSocketDisconnect:
        # 处理断开连接
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket错误: {e}")
        manager.disconnect(websocket)


# 健康检查和统计
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "statistics": {
            "total_rooms": len(manager.rooms),
            "total_connections": sum(len(conns) for conns in manager.rooms.values()),
            "total_history_messages": sum(len(history) for history in manager.history.values()),
            "active_since": min(
                (stats["created_at"] for stats in manager.room_stats.values()),
                default=time.time()
            )
        }
    }


@app.get("/stats")
async def get_stats():
    """获取详细统计信息"""
    total_rooms = len(manager.rooms)
    total_connections = sum(len(conns) for conns in manager.rooms.values())
    total_history = sum(len(history) for history in manager.history.values())
    
    rooms_info = []
    for room_name in manager.rooms.keys():
        room_info = manager.get_room_info(room_name)
        if room_info:
            rooms_info.append(room_info.dict())
    
    # 清理不活跃房间
    cleaned = manager.cleanup_inactive_rooms()
    
    return {
        "summary": {
            "total_rooms": total_rooms,
            "total_connections": total_connections,
            "total_history_messages": total_history,
            "cleaned_inactive_rooms": cleaned
        },
        "rooms": rooms_info,
        "timestamp": time.time(),
        "server_info": {
            "max_history_per_room": 50,
            "supports": ["websocket", "multiple_rooms", "nicknames", "history", "room_stats"]
        }
    }


# 运行应用
if __name__ == "__main__":
    import uvicorn
    
    print("启动WebSocket聊天服务器...")
    print(f"访问地址: http://localhost:8000")
    print(f"WebSocket地址: ws://localhost:8000/ws/房间名")
    print("\n可用接口:")
    print("- GET / - 聊天界面")
    print("- GET /rooms - 所有房间列表")
    print("- GET /rooms/{room} - 房间详情")
    print("- GET /rooms/{room}/users - 房间用户列表")
    print("- GET /rooms/{room}/history - 历史消息")
    print("- GET /health - 健康检查")
    print("- GET /stats - 统计信息")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)