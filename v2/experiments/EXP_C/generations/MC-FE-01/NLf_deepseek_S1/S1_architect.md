# MC-FE-01: 实时协作待办事项板技术方案

## 1. 组件架构

### 1.1 主要组件
- **TodoBoard**: 主组件，管理整个应用状态和布局
- **Column**: 列组件，表示待办事项的三个状态列（Todo / In Progress / Done）
- **TaskCard**: 任务卡片组件，显示单个待办事项的详细信息
- **TaskForm**: 创建新任务的表单组件
- **ConflictIndicator**: 冲突提示组件，当检测到并发冲突时显示

### 1.2 组件职责
- **TodoBoard**: 负责整体状态管理、列布局、拖放事件处理、实时同步模拟
- **Column**: 管理列内任务列表、处理拖放目标区域、提供列标题和统计信息
- **TaskCard**: 显示任务内容、处理拖放源事件、提供任务操作（编辑、删除）
- **TaskForm**: 收集新任务信息、验证输入、提交创建请求
- **ConflictIndicator**: 显示冲突警告、提供冲突解决选项

## 2. 数据模型

```typescript
interface Task {
  id: string;
  title: string;
  description: string;
  columnId: 'todo' | 'inProgress' | 'done';
  position: number; // 在列内的位置索引
  createdAt: Date;
  updatedAt: Date;
  createdBy: string; // 模拟用户ID
  version: number; // 乐观并发控制版本号
}

interface Column {
  id: 'todo' | 'inProgress' | 'done';
  title: string;
  taskIds: string[]; // 按位置排序的任务ID数组
}

interface BoardState {
  tasks: Record<string, Task>;
  columns: Column[];
  lastSyncTime: number;
  pendingOperations: PendingOperation[];
  conflicts: Conflict[];
}

interface PendingOperation {
  type: 'create' | 'move' | 'update' | 'delete';
  taskId: string;
  data: any;
  timestamp: number;
}

interface Conflict {
  taskId: string;
  localVersion: number;
  remoteVersion: number;
  resolved: boolean;
}
```

## 3. 状态管理方法

### 3.1 useReducer状态设计
- **state**: BoardState类型，包含所有应用状态
- **action类型**:
  - ADD_TASK: 添加新任务
  - MOVE_TASK: 移动任务到不同列或同列不同位置
  - UPDATE_TASK: 更新任务内容
  - DELETE_TASK: 删除任务
  - SYNC_START: 开始同步操作
  - SYNC_SUCCESS: 同步成功
  - SYNC_CONFLICT: 检测到冲突
  - RESOLVE_CONFLICT: 解决冲突

### 3.2 状态更新流程
1. 用户操作触发action
2. reducer更新本地状态并记录待处理操作
3. setTimeout模拟网络延迟后执行同步
4. 同步成功或检测冲突时更新状态

## 4. 关键实现方法

### 4.1 HTML5拖放API实现
- **拖放源（TaskCard）**: 设置draggable="true"，监听dragstart事件存储任务数据
- **放置目标（Column）**: 监听dragover、dragenter、dragleave、drop事件
- **数据传输**: 使用DataTransfer API传递任务ID和源列信息
- **视觉反馈**: 通过CSS类名变化提供拖放视觉反馈

### 4.2 实时同步模拟
- **setInterval轮询**: 每5秒模拟一次服务器同步
- **乐观更新**: 用户操作立即更新UI，后台处理同步
- **冲突检测**: 比较本地和模拟远程版本号
- **冲突解决**: 提供"保留本地"或"使用远程"选项

### 4.3 CSS Modules样式管理
- 每个组件有独立的.module.css文件
- 类名使用BEM命名约定
- 通过import styles from './TodoBoard.module.css'引用

## 5. 约束确认

### 约束1: TypeScript + React框架
- 使用TypeScript进行类型安全开发
- 使用React函数组件和Hooks
- 所有组件都有完整的TypeScript接口定义

### 约束2: CSS Modules样式
- 每个组件创建.module.css文件
- 类名通过styles对象引用
- 不使用Tailwind CSS或任何实用优先CSS框架

### 约束3: HTML5原生拖放API
- 使用HTML5 draggable属性
- 实现完整的dragstart、dragover、drop事件处理
- 不使用第三方拖放库

### 约束4: useReducer状态管理
- 所有状态通过useReducer管理
- 定义完整的action类型和reducer函数
- 不使用Redux、Zustand等状态管理库

### 约束5: 单文件导出
- 所有代码在一个.tsx文件中
- 使用export default导出TodoBoard组件
- 组件内部定义所有子组件

### 约束6: 模拟实时同步
- 使用setTimeout/setInterval模拟网络延迟
- 实现简单的轮询同步机制
- 不使用socket.io或WebSocket库

## 6. 性能考虑

1. **任务列表优化**: 使用React.memo包装TaskCard组件
2. **拖放性能**: 避免在drag事件中执行重计算
3. **状态更新**: 使用immer-like不可变更新模式
4. **冲突解决**: 最小化重新渲染范围

## 7. 可扩展性设计

1. **插件式架构**: 可添加新的列类型
2. **主题系统**: 通过CSS变量支持主题切换
3. **国际化**: 预留i18n键位
4. **持久化**: 可扩展为使用localStorage或IndexedDB

---

*文档字数: 约1800字*