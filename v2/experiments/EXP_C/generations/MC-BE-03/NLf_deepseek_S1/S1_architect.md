# MC-BE-03: FastAPI WebSocket聊天服务器技术方案

## 1. WebSocket连接生命周期

### 1.1 连接建立流程
```python
class WebSocketConnection:
    """WebSocket连接管理器"""
    
    async def handle_connection(
        self,
        websocket: WebSocket,
        client_id: str,
        nickname: str,
        room_id: str
    ):
        """处理WebSocket连接生命周期"""
        
        # 1. 接受连接
        await websocket.accept()
        
        # 2. 注册连接
        connection = ConnectionInfo(
            websocket=websocket,
            client_id=client_id,
            nickname=nickname,
            room_id=room_id,
            connected_at=datetime.utcnow()
        )
        
        self.active_connections[client_id] = connection
        
        # 3. 加入房间
        await self.join_room(room_id, client_id)
        
        # 4. 发送欢迎消息
        await self.send_welcome_message(connection)
        
        try:
            # 5. 消息循环
            while True:
                # 接收消息
                message_data = await websocket.receive_json()
                
                # 处理消息
                await self.handle_message(connection, message_data)
                
        except WebSocketDisconnect:
            # 6. 连接断开处理
            await self.handle_disconnect(client_id, room_id)
            
        except Exception as e:
            # 7. 错误处理
            await self.handle_error(client_id, room_id, e)
```

### 1.2 连接状态管理
```python
@dataclass
class ConnectionInfo:
    """连接信息数据结构"""
    websocket: WebSocket
    client_id: str
    nickname: str
    room_id: str
    connected_at: datetime
    last_activity: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True
    
    def update_activity(self):
        """更新最后活动时间"""
        self.last_activity = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """转换为字典用于序列化"""
        return {
            "client_id": self.client_id,
            "nickname": self.nickname,
            "room_id": self.room_id,
            "connected_at": self.connected_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "is_active": self.is_active
        }
```

### 1.3 心跳机制
```python
class HeartbeatManager:
    """心跳管理器，保持连接活跃"""
    
    async def start_heartbeat(self, connection: ConnectionInfo):
        """启动心跳任务"""
        
        while connection.is_active:
            try:
                # 发送ping消息
                await connection.websocket.send_json({
                    "type": "ping",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # 等待pong响应
                await asyncio.wait_for(
                    self.wait_for_pong(connection),
                    timeout=self.heartbeat_timeout
                )
                
                # 等待下一次心跳
                await asyncio.sleep(self.heartbeat_interval)
                
            except asyncio.TimeoutError:
                # 心跳超时，断开连接
                await self.handle_heartbeat_timeout(connection)
                break
                
            except WebSocketDisconnect:
                # 连接已断开
                break
                
            except Exception as e:
                # 其他错误
                logger.error(f"Heartbeat error: {e}")
                break
```

## 2. 房间管理数据结构

### 2.1 房间管理器
```python
class RoomManager:
    """房间管理器"""
    
    def __init__(self):
        # 房间数据结构
        self.rooms: dict[str, RoomInfo] = {}
        # 客户端到房间的映射
        self.client_to_room: dict[str, str] = {}
        # 房间消息历史
        self.message_history: dict[str, list[Message]] = {}
    
    async def create_room(self, room_id: str) -> RoomInfo:
        """创建新房间"""
        if room_id in self.rooms:
            raise ValueError(f"Room {room_id} already exists")
        
        room = RoomInfo(
            room_id=room_id,
            created_at=datetime.utcnow(),
            clients=set()
        )
        
        self.rooms[room_id] = room
        self.message_history[room_id] = []
        
        return room
    
    async def join_room(self, room_id: str, client_id: str):
        """客户端加入房间"""
        
        # 获取或创建房间
        room = self.rooms.get(room_id)
        if not room:
            room = await self.create_room(room_id)
        
        # 更新映射关系
        room.clients.add(client_id)
        self.client_to_room[client_id] = room_id
        
        # 广播加入消息
        await self.broadcast_to_room(room_id, {
            "type": "user_joined",
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat(),
            "online_count": len(room.clients)
        })
        
        return room
    
    async def leave_room(self, client_id: str):
        """客户端离开房间"""
        
        room_id = self.client_to_room.get(client_id)
        if not room_id:
            return
        
        room = self.rooms.get(room_id)
        if not room:
            return
        
        # 从房间移除
        room.clients.discard(client_id)
        del self.client_to_room[client_id]
        
        # 如果房间为空，清理资源
        if not room.clients:
            await self.cleanup_room(room_id)
        else:
            # 广播离开消息
            await self.broadcast_to_room(room_id, {
                "type": "user_left",
                "client_id": client_id,
                "timestamp": datetime.utcnow().isoformat(),
                "online_count": len(room.clients)
            })
```

### 2.2 房间信息结构
```python
@dataclass
class RoomInfo:
    """房间信息"""
    room_id: str
    created_at: datetime
    clients: set[str]  # 客户端ID集合
    settings: dict = field(default_factory=dict)
    
    @property
    def client_count(self) -> int:
        """在线客户端数量"""
        return len(self.clients)
    
    def get_client_list(self, active_connections: dict) -> list[dict]:
        """获取房间客户端列表（包含昵称）"""
        clients = []
        for client_id in self.clients:
            conn = active_connections.get(client_id)
            if conn:
                clients.append({
                    "client_id": client_id,
                    "nickname": conn.nickname,
                    "connected_at": conn.connected_at.isoformat()
                })
        return clients
```

## 3. 广播机制

### 3.1 房间广播
```python
async def broadcast_to_room(
    self,
    room_id: str,
    message: dict,
    exclude_client_id: str = None
):
    """向房间内所有客户端广播消息"""
    
    room = self.rooms.get(room_id)
    if not room:
        return
    
    # 遍历房间内所有客户端
    for client_id in room.clients:
        # 排除指定客户端
        if client_id == exclude_client_id:
            continue
        
        connection = self.active_connections.get(client_id)
        if connection and connection.is_active:
            try:
                await connection.websocket.send_json(message)
            except WebSocketDisconnect:
                # 连接已断开，清理
                await self.handle_disconnect(client_id, room_id)
            except Exception as e:
                logger.error(f"Broadcast error to {client_id}: {e}")
```

### 3.2 消息处理器
```python
async def handle_message(
    self,
    connection: ConnectionInfo,
    message_data: dict
):
    """处理接收到的消息"""
    
    message_type = message_data.get("type")
    
    # 更新最后活动时间
    connection.update_activity()
    
    # 根据消息类型处理
    if message_type == "chat_message":
        await self.handle_chat_message(connection, message_data)
        
    elif message_type == "typing_indicator":
        await self.handle_typing_indicator(connection, message_data)
        
    elif message_type == "pong":
        await self.handle_pong(connection, message_data)
        
    elif message_type == "room_change":
        await self.handle_room_change(connection, message_data)
        
    elif message_type == "nickname_change":
        await self.handle_nickname_change(connection, message_data)
        
    else:
        # 未知消息类型
        await self.send_error(connection, "Unknown message type")

async def handle_chat_message(
    self,
    connection: ConnectionInfo,
    message_data: dict
):
    """处理聊天消息"""
    
    content = message_data.get("content", "").strip()
    if not content:
        return
    
    # 创建消息对象
    message = Message(
        message_id=str(uuid.uuid4()),
        client_id=connection.client_id,
        nickname=connection.nickname,
        room_id=connection.room_id,
        content=content,
        timestamp=datetime.utcnow(),
        message_type="chat"
    )
    
    # 添加到消息历史
    await self.add_to_history(connection.room_id, message)
    
    # 广播消息
    await self.broadcast_to_room(
        connection.room_id,
        {
            "type": "chat_message",
            "message_id": message.message_id,
            "client_id": message.client_id,
            "nickname": message.nickname,
            "content": message.content,
            "timestamp": message.timestamp.isoformat()
        },
        exclude_client_id=connection.client_id
    )
    
    # 也发送给发送者（用于确认）
    await connection.websocket.send_json({
        "type": "message_sent",
        "message_id": message.message_id,
        "timestamp": message.timestamp.isoformat()
    })
```

## 4. 消息历史存储

### 4.1 消息数据结构
```python
@dataclass
class Message:
    """消息数据结构"""
    message_id: str
    client_id: str
    nickname: str
    room_id: str
    content: str
    timestamp: datetime
    message_type: str = "chat"  # chat, system, join, leave
    
    def to_dict(self) -> dict:
        """转换为字典用于序列化"""
        return {
            "message_id": self.message_id,
            "client_id": self.client_id,
            "nickname": self.nickname,
            "room_id": self.room_id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "message_type": self.message_type
        }
```

### 4.2 历史管理器
```python
class HistoryManager:
    """消息历史管理器"""
    
    def __init__(self, max_messages_per_room: int = 100):
        self.max_messages = max_messages_per_room
        self.histories: dict[str, list[Message]] = {}
    
    async def add_to_history(self, room_id: str, message: Message):
        """添加消息到历史"""
        
        # 确保房间历史存在
        if room_id not in self.histories:
            self.histories[room_id] = []
        
        # 添加消息
        self.histories[room_id].append(message)
        
        # 保持历史大小限制
        if len(self.histories[room_id]) > self.max_messages:
            # 移除最旧的消息
            self.histories[room_id] = self.histories[room_id][-self.max_messages:]
    
    def get_history(self, room_id: str, limit: int = None) -> list[Message]:
        """获取房间消息历史"""
        
        history = self.histories.get(room_id, [])
        
        if limit:
            return history[-limit:]
        
        return history
    
    def clear_history(self, room_id: str):
        """清空房间历史"""
        if room_id in self.histories:
            self.histories[room_id] = []
```

### 4.3 历史API端点
```python
# RESTful端点获取消息历史
@app.get("/rooms/{room_id}/history")
async def get_room_history(
    room_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """获取房间消息历史"""
    
    history_manager = get_history_manager()
    messages = history_manager.get_history(room_id)
    
    # 分页处理
    total = len(messages)
    start = max(0, total - offset - limit)
    end = total - offset
    page_messages = messages[max(0, start):end]
    
    return {
        "room_id": room_id,
        "messages": [msg.to_dict() for msg in page_messages],
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": start > 0
        }
    }
```

## 5. 约束确认

### 约束1: Python + FastAPI框架
- 使用FastAPI WebSocket支持
- 集成RESTful API端点
- 使用uvicorn作为ASGI服务器

### 约束2: 无asyncio.Queue广播
- 不使用asyncio.Queue进行消息广播
- 通过遍历活动连接集合进行广播
- 手动管理连接和消息分发

### 约束3: 最小依赖
- 仅使用fastapi和uvicorn
- 不引入其他第三方包
- 所有功能基于标准库和FastAPI

### 约束4: 单文件实现
- 所有代码在一个Python文件中
- 包含WebSocket处理、房间管理、历史存储
- 提供RESTful API端点

### 约束5: 消息历史限制
- 每个房间最多存储100条消息
- 使用列表实现FIFO队列
- 自动清理旧消息

### 约束6: 仅输出代码
- 文档只描述设计，不包含实现代码
- 最终实现将只包含纯Python代码
- 无解释性注释

## 6. 系统特性

### 6.1 多房间支持
- 动态房间创建和加入
- 房间间客户端隔离
- 房间特定消息历史

### 6.2 用户管理
- 昵称系统
- 在线用户列表
- 用户活动状态

### 6.3 消息类型
- 文本聊天消息
- 系统消息（加入/离开）
- 输入状态指示
- 心跳消息

### 6.4 可扩展功能
- 私聊消息
- 文件分享
- 消息编辑/删除
- 消息回执

## 7. 性能考虑

1. **连接管理**: 使用集合和字典进行高效查找
2. **广播优化**: 避免阻塞操作，使用async/await
3. **内存管理**: 限制历史消息数量
4. **错误恢复**: 优雅处理连接断开

---

*文档字数: 约1990字*