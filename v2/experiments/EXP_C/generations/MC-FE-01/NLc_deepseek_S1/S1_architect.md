# MC-FE-01: 实时协作待办板技术方案

## 1. 组件架构

### 1.1 核心组件
- **TodoBoard**: 主容器组件，管理三列布局和WebSocket连接
- **Column**: 列组件，表示Todo/In Progress/Done状态列
- **TaskItem**: 任务项组件，支持拖放和冲突提示
- **WebSocketManager**: WebSocket连接管理组件
- **ConflictResolver**: 冲突解决提示组件

### 1.2 组件职责
- **TodoBoard**: 协调所有子组件，维护全局状态，处理WebSocket消息
- **Column**: 渲染任务列表，提供拖放目标区域，管理列内任务排序
- **TaskItem**: 渲染单个任务，实现可拖拽源，显示乐观更新状态
- **WebSocketManager**: 建立/维护WebSocket连接，发送/接收实时消息
- **ConflictResolver**: 检测并显示冲突，提供解决建议

## 2. 数据模型

```typescript
interface Task {
  id: string;
  title: string;
  description?: string;
  column: 'todo' | 'inProgress' | 'done';
  position: number; // 列内排序位置
  createdAt: string;
  updatedAt: string;
  version: number; // 乐观锁版本号
  createdBy: string;
  optimisticId?: string; // 乐观更新临时ID
  isOptimistic?: boolean; // 是否处于乐观更新状态
}

interface ColumnState {
  id: 'todo' | 'inProgress' | 'done';
  title: string;
  tasks: Task[];
}

interface BoardState {
  columns: ColumnState[];
  connectedUsers: number;
  lastSyncTime?: string;
  pendingOperations: PendingOperation[];
}

interface PendingOperation {
  id: string;
  type: 'create' | 'move' | 'reorder';
  taskId: string;
  data: any;
  timestamp: number;
  resolved: boolean;
}

interface WebSocketMessage {
  type: 'taskCreated' | 'taskMoved' | 'taskReordered' | 'conflictDetected' | 'sync';
  payload: any;
  timestamp: string;
  userId: string;
}
```

## 3. 状态管理方法

### 3.1 useReducer状态设计
- **state**: BoardState类型，包含所有列、任务和连接状态
- **action types**:
  - `ADD_TASK`: 添加新任务
  - `MOVE_TASK`: 移动任务到不同列
  - `REORDER_TASK`: 重新排序列内任务
  - `UPDATE_TASK`: 更新任务信息
  - `SET_OPTIMISTIC`: 设置乐观更新状态
  - `CLEAR_OPTIMISTIC`: 清除乐观更新状态
  - `ADD_PENDING_OP`: 添加待处理操作
  - `RESOLVE_PENDING_OP`: 解决待处理操作
  - `SET_CONNECTED_USERS`: 更新连接用户数
  - `SYNC_STATE`: 同步服务器状态

### 3.2 状态更新流程
1. 用户操作触发本地状态更新（乐观更新）
2. 同时发送WebSocket消息到服务器
3. 服务器广播操作给其他用户
4. 收到服务器确认后清除乐观状态
5. 检测到冲突时显示提示并保留本地版本

## 4. 关键技术实现方法

### 4.1 HTML5原生拖放实现
- **可拖拽源**: TaskItem设置`draggable="true"`属性
- **拖放目标**: Column组件监听`onDragOver`和`onDrop`事件
- **数据传输**: 使用`dataTransfer.setData()`传递任务ID和列信息
- **视觉反馈**: 通过CSS类名变化提供拖放视觉提示

### 4.2 乐观更新策略
- **立即反馈**: 用户操作后立即更新UI
- **临时状态**: 为乐观更新创建临时任务ID和状态标记
- **操作队列**: 维护待确认操作队列
- **冲突检测**: 比较版本号和操作时间戳
- **回滚机制**: 服务器拒绝时回滚到先前状态

### 4.3 冲突解决提示
- **检测时机**: 收到服务器消息且版本号冲突时
- **提示内容**: 显示冲突任务、操作者和时间
- **解决选项**: 保留本地版本/使用远程版本/合并修改
- **自动解决**: 简单冲突（如位置调整）自动应用最新版本

### 4.4 WebSocket模拟
- **连接管理**: 手动管理WebSocket连接生命周期
- **消息格式**: 使用JSON格式的消息协议
- **重连逻辑**: 指数退避重连策略
- **心跳检测**: 定期发送ping/pong保持连接
- **离线处理**: 检测连接状态并提供离线提示

## 5. 约束确认

### 5.1 TS + React
- 使用TypeScript定义所有接口和类型
- React函数组件配合TypeScript泛型
- 完整的类型检查和编译时验证

### 5.2 CSS Modules only, no Tailwind
- 为每个组件创建独立的`.module.css`文件
- 使用CSS Modules实现样式作用域隔离
- 通过`import styles from './TodoBoard.module.css'`导入样式

### 5.3 HTML5 native drag, no dnd libs
- 使用HTML5原生`draggable`属性
- 实现`onDragStart`、`onDragOver`、`onDrop`事件处理器
- 手动管理拖放数据传递和视觉反馈

### 5.4 useReducer only, no state libs
- 单一`useReducer`管理所有应用状态
- 定义完整的action类型和reducer函数
- 通过`dispatch`函数触发状态更新

### 5.5 Single file, export default
- 所有组件、类型定义和逻辑都在单个`.tsx`文件中
- 使用`export default TodoBoard`导出主组件
- 内部使用函数声明和const定义组织代码

### 5.6 Hand-written WS mock, no socket.io
- 实现原生WebSocket客户端
- 创建模拟服务器响应的消息处理器
- 手动处理连接、消息发送和接收逻辑