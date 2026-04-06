# MC-BE-03: WebSocket聊天服务器技术方案

## 1. WebSocket连接生命周期

### 1.1 连接建立流程
```
1. 客户端发起WebSocket连接请求
2. 服务器验证连接（可选认证）
3. 建立WebSocket连接
4. 分配连接ID和用户信息
5. 加入默认房间或指定房间
6. 发送欢迎消息和在线用户列表
```

### 1.2 连接状态管理
```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Set, List, Optional
import asyncio

@dataclass
class ConnectionState:
    """WebSocket连接状态"""
    connection_id: str
    websocket: any  # WebSocket对象
    user_id: Optional[str] = None
    nickname: Optional[str] = None
    rooms: Set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    is_alive: bool = True
    
    def update_activity(self):
        """更新最后活动时间"""
        self.last_activity = datetime.utcnow()
    
    def join_room(self, room_id: str):
        """加入房间"""
        self.rooms.add(room_id)
    
    def leave_room(self, room_id: str):
        """离开房间"""
        self.rooms.discard(room_id)
    
    def disconnect(self):
        """断开连接"""
        self.is_alive = False
        self.rooms.clear()
```

### 1.3 心跳检测机制
```python
class HeartbeatManager:
    """心跳检测管理器"""
    
    def __init__(self, check_interval_seconds: int = 30, timeout_seconds: int = 60):
        self.check_interval = check_interval_seconds
        self.timeout = timeout_seconds
        self.connections: Dict[str, ConnectionState] = {}
    
    async def start_heartbeat_check(self):
        """启动心跳检测循环"""
        while True:
            await asyncio.sleep(self.check_interval)
            await self._check_connections()
    
    async def _check_connections(self):
        """检查连接活跃度"""
        current_time = datetime.utcnow()
        disconnected = []
        
        for conn_id, conn_state in self.connections.items():
            # 计算不活跃时间
            inactive_time = (current_time - conn_state.last_activity).total_seconds()
            
            if inactive_time > self.timeout:
                # 发送ping测试
                try:
                    await conn_state.websocket.ping()
                    conn_state.update_activity()
                except Exception:
                    # 连接已断开
                    disconnected.append(conn_id)
        
        # 清理断开连接
        for conn_id in disconnected:
            await self._cleanup_connection(conn_id)
```

## 2. 房间管理数据结构

### 2.1 房间状态设计
```python
@dataclass
class ChatRoom:
    """聊天房间"""
    room_id: str
    name: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    max_messages: int = 100
    connections: Set[str] = field(default_factory=set)  # 连接ID集合
    messages: List["ChatMessage"] = field(default_factory=list)
    is_public: bool = True
    
    def add_connection(self, connection_id: str):
        """添加连接到房间"""
        self.connections.add(connection_id)
    
    def remove_connection(self, connection_id: str):
        """从房间移除连接"""
        self.connections.discard(connection_id)
    
    def add_message(self, message: "ChatMessage"):
        """添加消息到房间"""
        self.messages.append(message)
        
        # 限制消息数量
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def get_recent_messages(self, count: int = 20) -> List["ChatMessage"]:
        """获取最近的消息"""
        return self.messages[-count:] if self.messages else []
    
    def get_online_count(self) -> int:
        """获取在线用户数"""
        return len(self.connections)
```

### 2.2 消息数据结构
```python
@dataclass
class ChatMessage:
    """聊天消息"""
    message_id: str
    room_id: str
    sender_id: str
    sender_nickname: str
    content: str
    message_type: str = "text"  # text, image, system
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, any]:
        """转换为字典格式"""
        return {
            "message_id": self.message_id,
            "room_id": self.room_id,
            "sender_id": self.sender_id,
            "sender_nickname": self.sender_nickname,
            "content": self.content,
            "message_type": self.message_type,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
```

### 2.3 房间管理器
```python
class RoomManager:
    """房间管理器"""
    
    def __init__(self):
        self.rooms: Dict[str, ChatRoom] = {}
        self.default_room_id = "general"
        
        # 创建默认房间
        self.create_room(self.default_room_id, "General Chat")
    
    def create_room(self, room_id: str, name: str, is_public: bool = True) -> ChatRoom:
        """创建新房间"""
        if room_id in self.rooms:
            raise ValueError(f"Room {room_id} already exists")
        
        room = ChatRoom(room_id=room_id, name=name, is_public=is_public)
        self.rooms[room_id] = room
        return room
    
    def get_room(self, room_id: str) -> Optional[ChatRoom]:
        """获取房间"""
        return self.rooms.get(room_id)
    
    def list_public_rooms(self) -> List[Dict[str, any]]:
        """列出公共房间"""
        return [
            {
                "room_id": room.room_id,
                "name": room.name,
                "online_count": room.get_online_count(),
                "is_public": room.is_public
            }
            for room in self.rooms.values()
            if room.is_public
        ]
    
    async def broadcast_to_room(
        self,
        room_id: str,
        message: Dict[str, any],
        exclude_connection_id: Optional[str] = None
    ):
        """向房间内所有连接广播消息"""
        room = self.get_room(room_id)
        if not room:
            return
        
        # 获取所有连接
        connections = room.connections.copy()
        
        # 广播消息
        for conn_id in connections:
            if conn_id == exclude_connection_id:
                continue
            
            conn_state = connection_manager.get_connection(conn_id)
            if conn_state and conn_state.is_alive:
                try:
                    await conn_state.websocket.send_json(message)
                except Exception:
                    # 连接可能已断开
                    await self.handle_disconnection(conn_id)
```

## 3. 广播机制

### 3.1 迭代广播实现
```python
class BroadcastManager:
    """广播管理器（不使用asyncio.Queue）"""
    
    def __init__(self, room_manager: RoomManager, connection_manager: "ConnectionManager"):
        self.room_manager = room_manager
        self.connection_manager = connection_manager
    
    async def broadcast_message(
        self,
        room_id: str,
        message_data: Dict[str, any],
        exclude_connection_id: Optional[str] = None
    ):
        """广播消息到房间"""
        room = self.room_manager.get_room(room_id)
        if not room:
            return
        
        # 使用集合迭代进行广播
        connections_to_broadcast = room.connections.copy()
        
        # 准备广播任务
        broadcast_tasks = []
        
        for conn_id in connections_to_broadcast:
            if conn_id == exclude_connection_id:
                continue
            
            conn_state = self.connection_manager.get_connection(conn_id)
            if conn_state and conn_state.is_alive:
                # 创建发送任务
                task = self._send_to_connection(conn_state, message_data)
                broadcast_tasks.append(task)
        
        # 并发执行所有发送任务
        if broadcast_tasks:
            await asyncio.gather(*broadcast_tasks, return_exceptions=True)
    
    async def _send_to_connection(
        self,
        conn_state: ConnectionState,
        message_data: Dict[str, any]
    ):
        """向单个连接发送消息"""
        try:
            await conn_state.websocket.send_json(message_data)
        except Exception as e:
            # 发送失败，连接可能已断开
            print(f"Failed to send to connection {conn_state.connection_id}: {e}")
            await self.connection_manager.handle_disconnection(conn_state.connection_id)
    
    async def broadcast_system_message(
        self,
        room_id: str,
        content: str,
        metadata: Optional[Dict[str, any]] = None
    ):
        """广播系统消息"""
        system_message = {
            "type": "system_message",
            "room_id": room_id,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        await self.broadcast_message(room_id, system_message)
```

### 3.2 消息类型处理
```python
class MessageHandler:
    """消息处理器"""
    
    MESSAGE_TYPES = {
        "chat_message": "处理聊天消息",
        "join_room": "处理加入房间请求",
        "leave_room": "处理离开房间请求",
        "set_nickname": "处理设置昵称请求",
        "typing_indicator": "处理输入指示器",
        "ping": "处理心跳ping"
    }
    
    async def handle_message(
        self,
        connection_id: str,
        message_data: Dict[str, any]
    ):
        """处理接收到的消息"""
        message_type = message_data.get("type")
        
        if message_type == "chat_message":
            await self._handle_chat_message(connection_id, message_data)
        elif message_type == "join_room":
            await self._handle_join_room(connection_id, message_data)
        elif message_type == "leave_room":
            await self._handle_leave_room(connection_id, message_data)
        elif message_type == "set_nickname":
            await self._handle_set_nickname(connection_id, message_data)
        elif message_type == "ping":
            await self._handle_ping(connection_id, message_data)
        else:
            # 未知消息类型
            await self._send_error(connection_id, f"Unknown message type: {message_type}")
    
    async def _handle_chat_message(
        self,
        connection_id: str,
        message_data: Dict[str, any]
    ):
        """处理聊天消息"""
        conn_state = connection_manager.get_connection(connection_id)
        if not conn_state:
            return
        
        # 创建聊天消息
        chat_message = ChatMessage(
            message_id=str(uuid.uuid4()),
            room_id=message_data.get("room_id", "general"),
            sender_id=conn_state.connection_id,
            sender_nickname=conn_state.nickname or "Anonymous",
            content=message_data.get("content", ""),
            message_type="text",
            metadata=message_data.get("metadata", {})
        )
        
        # 保存到房间历史
        room = room_manager.get_room(chat_message.room_id)
        if room:
            room.add_message(chat_message)
        
        # 广播消息
        await broadcast_manager.broadcast_message(
            chat_message.room_id,
            {
                "type": "chat_message",
                **chat_message.to_dict()
            },
            exclude_connection_id=connection_id
        )
```

## 4. 消息历史存储

### 4.1 内存消息存储
```python
class MessageHistory:
    """消息历史管理器"""
    
    def __init__(self, max_messages_per_room: int = 100):
        self.max_messages = max_messages_per_room
        self.room_messages: Dict[str, List[ChatMessage]] = {}
    
    def add_message(self, room_id: str, message: ChatMessage):
        """添加消息到历史"""
        if room_id not in self.room_messages:
            self.room_messages[room_id] = []
        
        messages = self.room_messages[room_id]
        messages.append(message)
        
        # 限制消息数量
        if len(messages) > self.max_messages:
            self.room_messages[room_id] = messages[-self.max_messages:]
    
    def get_recent_messages(self, room_id: str, limit: int = 20) -> List[Dict[str, any]]:
        """获取最近消息"""
        if room_id not in self.room_messages:
            return []
        
        messages = self.room_messages[room_id]
        recent = messages[-limit:] if messages else []
        
        return [msg.to_dict() for msg in recent]
    
    def clear_room_history(self, room_id: str):
        """清空房间历史"""
        if room_id in self.room_messages:
            self.room_messages[room_id] = []
    
    def get_room_stats(self, room_id: str) -> Dict[str, any]:
        """获取房间统计信息"""
        if room_id not in self.room_messages:
            return {"message_count": 0, "last_message_time": None}
        
        messages = self.room_messages[room_id]
        last_message_time = messages[-1].timestamp if messages else None
        
        return {
            "message_count": len(messages),
            "last_message_time": last_message_time.isoformat() if last_message_time else None
        }
```

### 4.2 历史消息API端点
```python
@router.get("/rooms/{room_id}/history")
async def get_room_history(
    room_id: str,
    limit: int = Query(20, ge=1, le=100),
    before: Optional[str] = Query(None)  # 时间戳过滤
):
    """获取房间历史消息"""
    room = room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # 获取消息
    messages = message_history.get_recent_messages(room_id, limit)
    
    # 时间过滤（如果提供）
    if before:
        try:
            before_time = datetime.fromisoformat(before.replace('Z', '+00:00'))
            messages = [
                msg for msg in messages
                if datetime.fromisoformat(msg["timestamp"].replace('Z', '+00:00')) < before_time
            ][:limit]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid timestamp format")
    
    return {
        "room_id": room_id,
        "messages": messages,
        "total": len(messages),
        "has_more": len(messages) >= limit
    }

@router.get("/rooms/{room_id}/online")
async def get_online_users(room_id: str):
    """获取房间在线用户列表"""
    room = room_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    online_users = []
    for conn_id in room.connections:
        conn_state = connection_manager.get_connection(conn_id)
        if conn_state and conn_state.is_alive:
            online_users.append({
                "connection_id": conn_state.connection_id,
                "nickname": conn_state.nickname,
                "user_id": conn_state.user_id,
                "connected_at": conn_state.connected_at.isoformat(),
                "last_activity": conn_state.last_activity.isoformat()
            })
    
    return {
        "room_id": room_id,
        "online_count": len(online_users),
        "users": online_users
    }
```

## 5. 约束确认

### 5.1 Python + FastAPI
- 使用FastAPI构建WebSocket服务器
- Python类型注解和异步支持

### 5.2 No asyncio.Queue for broadcast, use set iteration
- 使用集合迭代进行广播
- 手动管理连接集合
- 不使用asyncio.Queue进行消息分发

### 5.3 fastapi + uvicorn only
- 仅使用FastAPI和Uvicorn
- 无额外依赖库

### 5.4 Single file
- 所有代码在单个Python文件中
- 包含WebSocket处理、房间管理和消息广播

### 5.5 In-memory list, max 100 msgs per room
- 使用内存列表存储消息
- 每个房间最多存储100条消息
- 自动清理旧消息

### 5.6 Code only
- 纯代码实现
- 无外部配置文件
- 自包含WebSocket聊天服务器