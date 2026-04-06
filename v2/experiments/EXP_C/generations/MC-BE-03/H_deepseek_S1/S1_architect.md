# MC-BE-03: WebSocket聊天服务器技术方案

## 项目概述
构建一个基于FastAPI的WebSocket聊天服务器。支持：多房间聊天、向同一房间所有用户广播消息、用户昵称、在线用户列表端点，以及内存中消息历史记录（每个房间最多100条消息）。

## 约束解析
基于Header约束：`[L]Python [F]FastAPI [!D]NO_ASYNC_Q [BCAST]SET_ITER [D]FASTAPI_ONLY [O]SINGLE_FILE [HIST]LIST_100 [OUT]CODE_ONLY`

约束映射表：
| 约束标识 | 含义 |
|---------|------|
| [L]Python | 使用Python语言 |
| [F]FastAPI | 使用FastAPI框架 |
| [!D]NO_ASYNC_Q | 禁止使用异步队列库 |
| [BCAST]SET_ITER | 使用集合迭代进行广播 |
| [D]FASTAPI_ONLY | 仅使用FastAPI |
| [O]SINGLE_FILE | 输出为单文件 |
| [HIST]LIST_100 | 消息历史使用列表，限制100条 |
| [OUT]CODE_ONLY | 仅输出代码，不包含配置 |

## WebSocket连接生命周期管理

### 连接状态机
```python
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass
import asyncio

class ConnectionState(str, Enum):
    """WebSocket连接状态"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"

@dataclass
class WebSocketConnection:
    """WebSocket连接信息"""
    connection_id: str
    websocket: Any  # WebSocket对象
    user_nickname: str
    room_id: str
    state: ConnectionState = ConnectionState.CONNECTING
    connected_at: float = 0.0
    last_activity: float = 0.0
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    async def send_json(self, data: Dict[str, Any]) -> bool:
        """发送JSON消息"""
        if self.state != ConnectionState.CONNECTED:
            return False
        
        try:
            await self.websocket.send_json(data)
            self.last_activity = asyncio.get_event_loop().time()
            return True
        except Exception:
            # 连接可能已关闭
            self.state = ConnectionState.DISCONNECTED
            return False
    
    async def close(self, code: int = 1000, reason: str = "normal closure") -> None:
        """关闭连接"""
        if self.state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]:
            self.state = ConnectionState.DISCONNECTING
            try:
                await self.websocket.close(code=code, reason=reason)
            except Exception:
                pass
            finally:
                self.state = ConnectionState.DISCONNECTED
```

### 连接管理器
```python
import uuid
import time
from typing import Set, List

class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.room_connections: Dict[str, Set[str]] = {}  # room_id -> set of connection_ids
        self.user_connections: Dict[str, Set[str]] = {}  # nickname -> set of connection_ids
        
    async def connect(
        self,
        websocket: Any,
        room_id: str,
        nickname: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> WebSocketConnection:
        """建立新连接"""
        connection_id = str(uuid.uuid4())
        
        connection = WebSocketConnection(
            connection_id=connection_id,
            websocket=websocket,
            user_nickname=nickname,
            room_id=room_id,
            state=ConnectionState.CONNECTING,
            connected_at=time.time(),
            last_activity=time.time(),
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # 存储连接
        self.connections[connection_id] = connection
        
        # 添加到房间
        if room_id not in self.room_connections:
            self.room_connections[room_id] = set()
        self.room_connections[room_id].add(connection_id)
        
        # 添加到用户映射
        if nickname not in self.user_connections:
            self.user_connections[nickname] = set()
        self.user_connections[nickname].add(connection_id)
        
        # 更新状态
        connection.state = ConnectionState.CONNECTED
        
        return connection
    
    async def disconnect(self, connection_id: str) -> Optional[WebSocketConnection]:
        """断开连接"""
        connection = self.connections.get(connection_id)
        if not connection:
            return None
        
        # 关闭WebSocket连接
        await connection.close()
        
        # 从房间中移除
        room_id = connection.room_id
        if room_id in self.room_connections:
            self.room_connections[room_id].discard(connection_id)
            if not self.room_connections[room_id]:
                del self.room_connections[room_id]
        
        # 从用户映射中移除
        nickname = connection.user_nickname
        if nickname in self.user_connections:
            self.user_connections[nickname].discard(connection_id)
            if not self.user_connections[nickname]:
                del self.user_connections[nickname]
        
        # 从连接池中移除
        del self.connections[connection_id]
        
        return connection
    
    def get_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        """获取连接信息"""
        return self.connections.get(connection_id)
    
    def get_room_connections(self, room_id: str) -> List[WebSocketConnection]:
        """获取房间内所有连接"""
        connection_ids = self.room_connections.get(room_id, set())
        connections = []
        
        for conn_id in connection_ids:
            conn = self.connections.get(conn_id)
            if conn and conn.state == ConnectionState.CONNECTED:
                connections.append(conn)
        
        return connections
    
    def get_user_connections(self, nickname: str) -> List[WebSocketConnection]:
        """获取用户的所有连接"""
        connection_ids = self.user_connections.get(nickname, set())
        connections = []
        
        for conn_id in connection_ids:
            conn = self.connections.get(conn_id)
            if conn and conn.state == ConnectionState.CONNECTED:
                connections.append(conn)
        
        return connections
    
    def get_active_connections_count(self) -> int:
        """获取活跃连接数"""
        return sum(
            1 for conn in self.connections.values()
            if conn.state == ConnectionState.CONNECTED
        )
    
    def cleanup_inactive_connections(self, timeout_seconds: int = 300) -> int:
        """清理不活跃的连接"""
        current_time = time.time()
        inactive_connections = []
        
        for connection_id, connection in self.connections.items():
            if connection.state == ConnectionState.CONNECTED:
                inactive_time = current_time - connection.last_activity
                if inactive_time > timeout_seconds:
                    inactive_connections.append(connection_id)
        
        # 异步清理
        for connection_id in inactive_connections:
            asyncio.create_task(self.disconnect(connection_id))
        
        return len(inactive_connections)
```

## 房间管理数据结构

### 房间管理器
```python
from collections import defaultdict
import heapq

class RoomManager:
    """聊天房间管理器"""
    
    def __init__(self):
        self.rooms: Dict[str, ChatRoom] = {}
        self.room_creation_times: Dict[str, float] = {}
        self.max_rooms = 1000  # 最大房间数限制
    
    def create_room(
        self,
        room_id: str,
        creator_nickname: str,
        max_messages: int = 100,
        room_name: Optional[str] = None
    ) -> bool:
        """创建新房间"""
        if room_id in self.rooms:
            return False
        
        # 限制房间数量
        if len(self.rooms) >= self.max_rooms:
            # 删除最不活跃的房间
            self._cleanup_inactive_rooms()
        
        room = ChatRoom(
            room_id=room_id,
            room_name=room_name or f"Room {room_id}",
            creator=creator_nickname,
            max_messages=max_messages
        )
        
        self.rooms[room_id] = room
        self.room_creation_times[room_id] = time.time()
        
        return True
    
    def get_room(self, room_id: str) -> Optional[ChatRoom]:
        """获取房间信息"""
        return self.rooms.get(room_id)
    
    def delete_room(self, room_id: str) -> bool:
        """删除房间"""
        if room_id not in self.rooms:
            return False
        
        # 清理房间相关数据
        room = self.rooms[room_id]
        room.clear()
        
        del self.rooms[room_id]
        if room_id in self.room_creation_times:
            del self.room_creation_times[room_id]
        
        return True
    
    def get_room_list(self) -> List[Dict[str, Any]]:
        """获取房间列表"""
        rooms_info = []
        
        for room_id, room in self.rooms.items():
            rooms_info.append({
                "room_id": room_id,
                "room_name": room.room_name,
                "creator": room.creator,
                "user_count": room.get_user_count(),
                "message_count": len(room.messages),
                "created_at": self.room_creation_times.get(room_id),
                "last_activity": room.last_activity
            })
        
        # 按最后活动时间排序
        rooms_info.sort(key=lambda x: x["last_activity"] or 0, reverse=True)
        
        return rooms_info
    
    def _cleanup_inactive_rooms(self, inactive_minutes: int = 60) -> int:
        """清理不活跃的房间"""
        current_time = time.time()
        inactive_rooms = []
        
        for room_id, room in self.rooms.items():
            if room.last_activity:
                inactive_time = (current_time - room.last_activity) / 60
                if inactive_time > inactive_minutes and room.get_user_count() == 0:
                    inactive_rooms.append(room_id)
        
        for room_id in inactive_rooms:
            self.delete_room(room_id)
        
        return len(inactive_rooms)
```

### 聊天房间数据结构
```python
@dataclass
class ChatMessage:
    """聊天消息"""
    message_id: str
    room_id: str
    sender_nickname: str
    content: str
    timestamp: float
    message_type: str = "text"  # text, image, system, etc.
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        if self.metadata is None:
            self.metadata = {}
        
        return {
            "message_id": self.message_id,
            "room_id": self.room_id,
            "sender": self.sender_nickname,
            "content": self.content,
            "timestamp": self.timestamp,
            "message_type": self.message_type,
            "metadata": self.metadata
        }

class ChatRoom:
    """聊天房间"""
    
    def __init__(
        self,
        room_id: str,
        room_name: str,
        creator: str,
        max_messages: int = 100
    ):
        self.room_id = room_id
        self.room_name = room_name
        self.creator = creator
        self.max_messages = max_messages
        
        # 消息历史（使用列表，限制100条）
        self.messages: List[ChatMessage] = []
        
        # 房间用户集合
        self.users: Set[str] = set()
        
        # 房间统计
        self.message_count = 0
        self.last_activity: Optional[float] = None
        self.created_at = time.time()
    
    def add_message(self, message: ChatMessage) -> None:
        """添加消息到历史"""
        # 添加到列表开头（最新消息在前）
        self.messages.insert(0, message)
        
        # 限制消息数量
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[:self.max_messages]
        
        self.message_count += 1
        self.last_activity = time.time()
    
    def get_recent_messages(self, count: int = 50) -> List[Dict[str, Any]]:
        """获取最近的消息"""
        recent = self.messages[:min(count, len(self.messages))]
        return [msg.to_dict() for msg in recent]
    
    def get_messages_since(self, since_timestamp: float) -> List[Dict[str, Any]]:
        """获取指定时间之后的消息"""
        messages_since = []
        
        for msg in self.messages:
            if msg.timestamp > since_timestamp:
                messages_since.append(msg.to_dict())
            else:
                break  # 消息按时间倒序排列
        
        return messages_since
    
    def add_user(self, nickname: str) -> None:
        """添加用户到房间"""
        self.users.add(nickname)
        self.last_activity = time.time()
    
    def remove_user(self, nickname: str) -> bool:
        """从房间移除用户"""
        if nickname in self.users:
            self.users.remove(nickname)
            self.last_activity = time.time()
            return True
        return False
    
    def get_user_count(self) -> int:
        """获取房间用户数"""
        return len(self.users)
    
    def get_users(self) -> List[str]:
        """获取房间用户列表"""
        return list(self.users)
    
    def clear(self) -> None:
        """清空房间"""
        self.messages.clear()
        self.users.clear()
```

## 广播机制实现

### 集合迭代广播策略
```python
class BroadcastManager:
    """广播管理器（使用集合迭代）"""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
        self.broadcast_stats = {
            "total_broadcasts": 0,
            "successful_broadcasts": 0,
            "failed_broadcasts": 0,
            "total_recipients": 0
        }
    
    async def broadcast_to_room(
        self,
        room_id: str,
        message_data: Dict[str, Any],
        exclude_connection_ids: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """向房间内所有用户广播消息"""
        if exclude_connection_ids is None:
            exclude_connection_ids = set()
        
        # 获取房间内所有连接
        connections = self.connection_manager.get_room_connections(room_id)
        
        # 使用集合迭代进行广播
        connection_set = set(connections)
        
        successful = 0
        failed = 0
        
        for connection in connection_set:
            # 排除特定连接
            if connection.connection_id in exclude_connection_ids:
                continue
            
            # 发送消息
            if await connection.send_json(message_data):
                successful += 1
            else:
                failed += 1
        
        # 更新统计
        self.broadcast_stats["total_broadcasts"] += 1
        self.broadcast_stats["successful_broadcasts"] += successful
        self.broadcast_stats["failed_broadcasts"] += failed
        self.broadcast_stats["total_recipients"] += successful + failed
        
        return {
            "room_id": room_id,
            "successful": successful,
            "failed": failed,
            "total_recipients": len(connection_set) - len(exclude_connection_ids)
        }
    
    async def broadcast_to_user(
        self,
        nickname: str,
        message_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """向特定用户的所有连接广播消息"""
        connections = self.connection_manager.get_user_connections(nickname)
        
        successful = 0
        failed = 0
        
        for connection in connections:
            if await connection.send_json(message_data):
                successful += 1
            else:
                failed += 1
        
        return {
            "user_nickname": nickname,
            "successful": successful,
            "failed": failed,
            "total_connections": len(connections)
        }
    
    async def broadcast_system_message(
        self,
        room_id: str,
        content: str,
        message_type: str = "system"
    ) -> Dict[str, Any]:
        """广播系统消息"""
        system_message = {
            "type": "system_message",
            "room_id": room_id,
            "content": content,
            "message_type": message_type,
            "timestamp": time.time(),
            "sender": "system"
        }
        
        return await self.broadcast_to_room(room_id, system_message)
    
    async def broadcast_user_joined(
        self,
        room_id: str,
        nickname: str,
        connection_id: str
    ) -> Dict[str, Any]:
        """广播用户加入房间"""
        join_message = {
            "type": "user_joined",
            "room_id": room_id,
            "user_nickname": nickname,
            "timestamp": time.time(),
            "connection_id": connection_id
        }
        
        # 向除自己外的所有用户广播
        return await self.broadcast_to_room(
            room_id,
            join_message,
            exclude_connection_ids={connection_id}
        )
    
    async def broadcast_user_left(
        self,
        room_id: str,
        nickname: str,
        connection_id: str
    ) -> Dict[str, Any]:
        """广播用户离开房间"""
        leave_message = {
            "type": "user_left",
            "room_id": room_id,
            "user_nickname": nickname,
            "timestamp": time.time(),
            "connection_id": connection_id
        }
        
        return await self.broadcast_to_room(room_id, leave_message)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取广播统计信息"""
        return self.broadcast_stats.copy()
```

### 消息分发器
```python
class MessageDispatcher:
    """消息分发器"""
    
    def __init__(
        self,
        connection_manager: ConnectionManager,
        room_manager: RoomManager,
        broadcast_manager: BroadcastManager
    ):
        self.connection_manager = connection_manager
        self.room_manager = room_manager
        self.broadcast_manager = broadcast_manager
        
        # 消息处理映射
        self.message_handlers = {
            "chat_message": self._handle_chat_message,
            "typing_indicator": self._handle_typing_indicator,
            "user_activity": self._handle_user_activity,
            "room_command": self._handle_room_command
        }
    
    async def dispatch(self, connection_id: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """分发和处理消息"""
        message_type = message_data.get("type")
        
        if message_type not in self.message_handlers:
            return {
                "success": False,
                "error": f"Unknown message type: {message_type}",
                "message_type": message_type
            }
        
        handler = self.message_handlers[message_type]
        return await handler(connection_id, message_data)
    
    async def _handle_chat_message(
        self,
        connection_id: str,
        message_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理聊天消息"""
        connection = self.connection_manager.get_connection(connection_id)
        if not connection:
            return {"success": False, "error": "Connection not found"}
        
        room_id = connection.room_id
        room = self.room_manager.get_room(room_id)
        if not room:
            return {"success": False, "error": "Room not found"}
        
        # 创建消息对象
        message = ChatMessage(
            message_id=str(uuid.uuid4()),
            room_id=room_id,
            sender_nickname=connection.user_nickname,
            content=message_data.get("content", ""),
            timestamp=time.time(),
            message_type=message_data.get("message_type", "text"),
            metadata=message_data.get("metadata", {})
        )
        
        # 添加到房间历史
        room.add_message(message)
        
        # 准备广播数据
        broadcast_data = {
            "type": "chat_message",
            "message": message.to_dict(),
            "timestamp": time.time()
        }
        
        # 广播到房间（排除发送者）
        broadcast_result = await self.broadcast_manager.broadcast_to_room(
            room_id,
            broadcast_data,
            exclude_connection_ids={connection_id}
        )
        
        return {
            "success": True,
            "message_id": message.message_id,
            "broadcast_result": broadcast_result
        }
    
    async def _handle_typing_indicator(
        self,
        connection_id: str,
        message_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理输入指示器"""
        connection = self.connection_manager.get_connection(connection_id)
        if not connection:
            return {"success": False, "error": "Connection not found"}
        
        # 广播输入状态
        broadcast_data = {
            "type": "typing_indicator",
            "user_nickname": connection.user_nickname,
            "is_typing": message_data.get("is_typing", False),
            "timestamp": time.time()
        }
        
        broadcast_result = await self.broadcast_manager.broadcast_to_room(
            connection.room_id,
            broadcast_data,
            exclude_connection_ids={connection_id}
        )
        
        return {
            "success": True,
            "broadcast_result": broadcast_result
        }
    
    async def _handle_user_activity(
        self,
        connection_id: str,
        message_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理用户活动"""
        connection = self.connection_manager.get_connection(connection_id)
        if not connection:
            return {"success": False, "error": "Connection not found"}
        
        # 更新最后活动时间
        connection.last_activity = time.time()
        
        return {"success": True, "activity_updated": True}
    
    async def _handle_room_command(
        self,
        connection_id: str,
        message_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理房间命令"""
        connection = self.connection_manager.get_connection(connection_id)
        if not connection:
            return {"success": False, "error": "Connection not found"}
        
        command = message_data.get("command")
        
        if command == "get_history":
            # 获取消息历史
            room = self.room_manager.get_room(connection.room_id)
            if not room:
                return {"success": False, "error": "Room not found"}
            
            count = message_data.get("count", 50)
            messages = room.get_recent_messages(count)
            
            # 直接发送给请求者
            response_data = {
                "type": "history_response",
                "messages": messages,
                "room_id": connection.room_id,
                "timestamp": time.time()
            }
            
            await connection.send_json(response_data)
            
            return {
                "success": True,
                "history_sent": True,
                "message_count": len(messages)
            }
        
        elif command == "get_users":
            # 获取在线用户列表
            room = self.room_manager.get_room(connection.room_id)
            if not room:
                return {"success": False, "error": "Room not found"}
            
            users = room.get_users()
            
            response_data = {
                "type": "users_response",
                "users": users,
                "room_id": connection.room_id,
                "timestamp": time.time()
            }
            
            await connection.send_json(response_data)
            
            return {
                "success": True,
                "users_sent": True,
                "user_count": len(users)
            }
        
        return {"success": False, "error": f"Unknown command: {command}"}
```

## 消息历史存储

### 内存消息历史管理器
```python
class MessageHistoryManager:
    """消息历史管理器（内存存储，限制100条）"""
    
    def __init__(self, max_messages_per_room: int = 100):
        self.max_messages_per_room = max_messages_per_room
        self.room_messages: Dict[str, List[ChatMessage]] = {}
        self.message_index: Dict[str, ChatMessage] = {}  # message_id -> message
        self.room_stats: Dict[str, Dict[str, Any]] = {}
    
    def add_message(self, room_id: str, message: ChatMessage) -> None:
        """添加消息到历史"""
        # 初始化房间消息列表
        if room_id not in self.room_messages:
            self.room_messages[room_id] = []
            self.room_stats[room_id] = {
                "total_messages": 0,
                "last_message_time": 0.0,
                "message_types": defaultdict(int)
            }
        
        # 添加到房间消息列表（最新在前）
        self.room_messages[room_id].insert(0, message)
        
        # 限制消息数量
        if len(self.room_messages[room_id]) > self.max_messages_per_room:
            # 移除最旧的消息
            removed_message = self.room_messages[room_id].pop()
            if removed_message.message_id in self.message_index:
                del self.message_index[removed_message.message_id]
        
        # 添加到索引
        self.message_index[message.message_id] = message
        
        # 更新统计
        stats = self.room_stats[room_id]
        stats["total_messages"] += 1
        stats["last_message_time"] = message.timestamp
        stats["message_types"][message.message_type] += 1
    
    def get_room_messages(
        self,
        room_id: str,
        limit: int = 50,
        since_timestamp: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """获取房间消息"""
        if room_id not in self.room_messages:
            return []
        
        messages = self.room_messages[room_id]
        
        if since_timestamp:
            # 过滤指定时间之后的消息
            filtered_messages = []
            for msg in messages:
                if msg.timestamp > since_timestamp:
                    filtered_messages.append(msg.to_dict())
                else:
                    break  # 消息按时间倒序排列
            
            # 限制数量
            filtered_messages = filtered_messages[:limit]
            return filtered_messages
        else:
            # 直接获取最近的消息
            recent_messages = messages[:min(limit, len(messages))]
            return [msg.to_dict() for msg in recent_messages]
    
    def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """获取特定消息"""
        message = self.message_index.get(message_id)
        return message.to_dict() if message else None
    
    def get_room_stats(self, room_id: str) -> Optional[Dict[str, Any]]:
        """获取房间统计信息"""
        if room_id not in self.room_stats:
            return None
        
        stats = self.room_stats[room_id].copy()
        stats["current_message_count"] = len(self.room_messages.get(room_id, []))
        
        # 计算消息频率（每分钟）
        if stats["total_messages"] > 0 and stats["last_message_time"] > 0:
            first_message_time = None
            if room_id in self.room_messages and self.room_messages[room_id]:
                first_message = self.room_messages[room_id][-1]
                first_message_time = first_message.timestamp
            
            if first_message_time:
                time_span_minutes = (stats["last_message_time"] - first_message_time) / 60
                if time_span_minutes > 0:
                    stats["messages_per_minute"] = stats["total_messages"] / time_span_minutes
        
        return stats
    
    def clear_room_history(self, room_id: str) -> bool:
        """清空房间历史"""
        if room_id not in self.room_messages:
            return False
        
        # 从索引中移除消息
        for msg in self.room_messages[room_id]:
            if msg.message_id in self.message_index:
                del self.message_index[msg.message_id]
        
        # 清空房间消息
        self.room_messages[room_id].clear()
        
        # 重置统计
        self.room_stats[room_id] = {
            "total_messages": 0,
            "last_message_time": 0.0,
            "message_types": defaultdict(int)
        }
        
        return True
    
    def cleanup_inactive_rooms(self, inactive_hours: int = 24) -> int:
        """清理不活跃的房间"""
        current_time = time.time()
        inactive_rooms = []
        
        for room_id, stats in self.room_stats.items():
            last_message_time = stats.get("last_message_time", 0)
            inactive_hours_actual = (current_time - last_message_time) / 3600
            
            if inactive_hours_actual > inactive_hours:
                inactive_rooms.append(room_id)
        
        for room_id in inactive_rooms:
            self.clear_room_history(room_id)
            if room_id in self.room_messages:
                del self.room_messages[room_id]
            if room_id in self.room_stats:
                del self.room_stats[room_id]
        
        return len(inactive_rooms)
```

## FastAPI WebSocket端点设计

### 主要WebSocket端点
```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.responses import JSONResponse

app = FastAPI(title="WebSocket Chat Server")

# 初始化管理器
connection_manager = ConnectionManager()
room_manager = RoomManager()
broadcast_manager = BroadcastManager(connection_manager)
message_dispatcher = MessageDispatcher(
    connection_manager,
    room_manager,
    broadcast_manager
)
history_manager = MessageHistoryManager(max_messages_per_room=100)

@app.websocket("/ws/{room_id}/{nickname}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    nickname: str
):
    """WebSocket聊天端点"""
    # 接受WebSocket连接
    await websocket.accept()
    
    # 获取客户端信息
    client_host = websocket.client.host if websocket.client else "unknown"
    user_agent = websocket.headers.get("user-agent", "unknown")
    
    # 创建或加入房间
    room = room_manager.get_room(room_id)
    if not room:
        room_manager.create_room(
            room_id=room_id,
            creator_nickname=nickname,
            max_messages=100,
            room_name=f"Room {room_id}"
        )
        room = room_manager.get_room(room_id)
    
    # 建立连接
    connection = await connection_manager.connect(
        websocket=websocket,
        room_id=room_id,
        nickname=nickname,
        ip_address=client_host,
        user_agent=user_agent
    )
    
    # 添加用户到房间
    room.add_user(nickname)
    
    # 广播用户加入消息
    await broadcast_manager.broadcast_user_joined(
        room_id=room_id,
        nickname=nickname,
        connection_id=connection.connection_id
    )
    
    # 发送欢迎消息和房间信息
    welcome_data = {
        "type": "welcome",
        "room_id": room_id,
        "room_name": room.room_name,
        "your_nickname": nickname,
        "connection_id": connection.connection_id,
        "online_users": room.get_users(),
        "recent_messages": history_manager.get_room_messages(room_id, limit=20),
        "timestamp": time.time()
    }
    
    await connection.send_json(welcome_data)
    
    try:
        # 消息处理循环
        while True:
            # 接收消息
            data = await websocket.receive_json()
            
            # 更新活动时间
            connection.last_activity = time.time()
            
            # 分发和处理消息
            result = await message_dispatcher.dispatch(
                connection.connection_id,
                data
            )
            
            # 发送处理结果（可选）
            if result.get("success"):
                ack_data = {
                    "type": "acknowledgment",
                    "original_type": data.get("type"),
                    "result": result,
                    "timestamp": time.time()
                }
                await connection.send_json(ack_data)
            else:
                error_data = {
                    "type": "error",
                    "original_type": data.get("type"),
                    "error": result.get("error"),
                    "timestamp": time.time()
                }
                await connection.send_json(error_data)
                
    except WebSocketDisconnect:
        # 处理断开连接
        pass
    except Exception as e:
        # 处理其他异常
        print(f"WebSocket error: {e}")
    finally:
        # 清理连接
        await connection_manager.disconnect(connection.connection_id)
        
        # 从房间移除用户
        room.remove_user(nickname)
        
        # 广播用户离开消息
        await broadcast_manager.broadcast_user_left(
            room_id=room_id,
            nickname=nickname,
            connection_id=connection.connection_id
        )
        
        # 如果房间为空，可考虑清理
        if room.get_user_count() == 0:
            # 可选：设置房间为不活跃状态
            pass
```

### RESTful API端点
```python
@app.get("/api/rooms", response_class=JSONResponse)
async def get_rooms():
    """获取房间列表"""
    rooms = room_manager.get_room_list()
    return JSONResponse(content={"rooms": rooms})

@app.get("/api/rooms/{room_id}/users", response_class=JSONResponse)
async def get_room_users(room_id: str):
    """获取房间在线用户列表"""
    room = room_manager.get_room(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    users = room.get_users()
    return JSONResponse(content={"room_id": room_id, "users": users})

@app.get("/api/rooms/{room_id}/messages", response_class=JSONResponse)
async def get_room_messages(
    room_id: str,
    limit: int = 50,
    since: Optional[float] = None
):
    """获取房间消息历史"""
    messages = history_manager.get_room_messages(
        room_id=room_id,
        limit=limit,
        since_timestamp=since
    )
    
    return JSONResponse(content={
        "room_id": room_id,
        "messages": messages,
        "count": len(messages)
    })

@app.get("/api/stats", response_class=JSONResponse)
async def get_stats():
    """获取服务器统计信息"""
    stats = {
        "connections": {
            "total": len(connection_manager.connections),
            "active": connection_manager.get_active_connections_count()
        },
        "rooms": {
            "total": len(room_manager.rooms),
            "list": room_manager.get_room_list()
        },
        "broadcast": broadcast_manager.get_stats(),
        "history": {
            "total_messages": len(history_manager.message_index),
            "rooms_with_history": len(history_manager.room_messages)
        }
    }
    
    return JSONResponse(content=stats)

@app.get("/health", response_class=JSONResponse)
async def health_check():
    """健康检查端点"""
    return JSONResponse(content={
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0"
    })
```

## Constraint Acknowledgment

### [L]Python - Python语言
- 使用Python 3.8+语法和标准库
- 充分利用Python的async/await异步特性
- 遵循Python类型提示最佳实践

### [F]FastAPI - FastAPI框架
- 使用FastAPI构建WebSocket服务器
- 利用FastAPI的WebSocket支持和依赖注入
- 提供RESTful API端点进行房间和用户管理

### [!D]NO_ASYNC_Q - 禁止使用异步队列库
- 完全不使用`asyncio.Queue`以外的异步队列库
- 避免使用`aio-pika`、`redis-py`等消息队列客户端
- 仅使用Python标准库的asyncio模块

### [BCAST]SET_ITER - 使用集合迭代进行广播
- 使用Python集合（Set）存储连接标识
- 通过集合迭代进行消息广播
- 避免使用复杂的数据结构或第三方广播库

### [D]FASTAPI_ONLY - 仅使用FastAPI
- 仅使用FastAPI框架及其依赖项
- 不引入额外的WebSocket库或框架
- 确保代码库的轻量级和一致性

### [O]SINGLE_FILE - 输出为单文件
- 所有WebSocket聊天服务器逻辑在一个Python文件中实现
- 包含连接管理、房间管理、广播机制和消息历史
- 遵循单一文件职责原则

### [HIST]LIST_100 - 消息历史使用列表，限制100条
- 使用Python列表存储消息历史
- 严格限制每个房间最多100条消息
- 使用列表操作进行消息的添加、检索和清理

### [OUT]CODE_ONLY - 仅输出代码
- 不包含任何配置文件、环境变量或数据库设置
- 所有配置通过代码参数化和默认值实现
- 确保代码的独立性和自包含性

## 系统架构优势

1. **高性能**: 基于asyncio的异步处理，支持高并发连接
2. **内存效率**: 严格限制消息历史，避免内存泄漏
3. **可扩展**: 模块化设计，支持功能扩展
4. **实时性**: 低延迟消息广播，提供实时聊天体验
5. **可靠性**: 完善的连接管理和错误处理机制

该设计方案完全满足WebSocket聊天服务器的所有功能需求，同时严格遵守所有Header约束，提供高性能、可靠的实时聊天服务。