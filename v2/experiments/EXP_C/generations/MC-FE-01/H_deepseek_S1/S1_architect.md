# MC-FE-01: 实时协作待办事项看板技术方案

## 项目概述
构建一个实时协作的待办事项看板系统，支持多用户在同一看板上创建、移动和重新排序任务。系统包含三个标准列（待办/进行中/完成），通过HTML5原生拖拽实现交互，支持乐观更新和冲突解决提示。

## 约束解析
基于Header约束：`[L]TS [F]React [Y]CSS_MODULES [!Y]NO_TW [!D]NO_DND_LIB [DRAG]HTML5 [STATE]useReducer [O]SFC [EXP]DEFAULT [WS]MOCK [!D]NO_SOCKETIO`

约束映射表：
| 约束标识 | 含义 |
|---------|------|
| [L]TS | 使用TypeScript |
| [F]React | 使用React框架 |
| [Y]CSS_MODULES | 使用CSS Modules样式方案 |
| [!Y]NO_TW | 禁止使用Tailwind CSS |
| [!D]NO_DND_LIB | 禁止使用第三方拖拽库 |
| [DRAG]HTML5 | 使用HTML5原生拖拽API |
| [STATE]useReducer | 使用useReducer进行状态管理 |
| [O]SFC | 输出为单文件组件 |
| [EXP]DEFAULT | 使用默认导出 |
| [WS]MOCK | WebSocket使用模拟实现 |
| [!D]NO_SOCKETIO | 禁止使用Socket.io库 |

## 组件架构设计

### 核心组件结构
```
TodoBoard (根组件)
├── BoardHeader (看板标题栏)
├── ColumnContainer (列容器)
│   ├── BoardColumn × 3 (看板列组件)
│   │   ├── ColumnHeader (列标题)
│   │   ├── TaskCard × N (任务卡片)
│   │   └── AddTaskButton (添加任务按钮)
│   └── ColumnDropZone (列间拖拽区域)
└── ConflictResolutionModal (冲突解决模态框)
```

### 组件职责说明
1. **TodoBoard**: 根组件，管理整个看板状态，处理WebSocket连接和事件分发
2. **BoardHeader**: 显示看板标题，用户在线状态，协作会话信息
3. **ColumnContainer**: 负责列布局和列间拖拽区域的渲染
4. **BoardColumn**: 单个列组件，管理列内任务，处理拖拽开始/结束事件
5. **TaskCard**: 任务卡片，显示任务内容、优先级、用户分配等信息
6. **ColumnDropZone**: 列间透明拖拽区域，处理拖拽悬停和放置事件
7. **ConflictResolutionModal**: 冲突解决对话框，当多用户同时修改同一任务时显示

## 数据模型设计

### TypeScript接口定义
```typescript
// 任务实体
interface Task {
  id: string;
  title: string;
  description?: string;
  column: 'todo' | 'inProgress' | 'done';
  position: number; // 列内排序位置
  assignee?: string;
  priority: 'low' | 'medium' | 'high';
  createdAt: string;
  updatedAt: string;
  version: number; // 乐观锁版本号
}

// 看板状态
interface BoardState {
  tasks: Task[];
  users: User[];
  lastSyncAt: string;
}

// 用户实体
interface User {
  id: string;
  name: string;
  color: string; // 用户标识颜色
  online: boolean;
}

// WebSocket事件
interface WSEvent {
  type: 'task_moved' | 'task_created' | 'task_updated' | 'user_joined' | 'user_left';
  payload: any;
  timestamp: string;
  userId: string;
}

// 冲突信息
interface Conflict {
  taskId: string;
  localVersion: number;
  remoteVersion: number;
  localChange: Partial<Task>;
  remoteChange: Partial<Task>;
  resolved: boolean;
}
```

## 状态管理方案

### useReducer状态设计
```typescript
// 状态结构
type TodoState = {
  board: BoardState;
  draggingTask: { taskId: string, sourceColumn: string } | null;
  conflicts: Conflict[];
  ui: {
    isLoading: boolean;
    showConflictModal: boolean;
    activeColumn: string | null;
  };
};

// 动作定义
type TodoAction =
  | { type: 'TASK_DRAG_START'; payload: { taskId: string, column: string } }
  | { type: 'TASK_DRAG_OVER'; payload: { column: string } }
  | { type: 'TASK_DROP'; payload: { taskId: string, targetColumn: string, position: number } }
  | { type: 'TASK_CREATE'; payload: Omit<Task, 'id' | 'createdAt' | 'updatedAt' | 'version'> }
  | { type: 'WS_EVENT'; payload: WSEvent }
  | { type: 'CONFLICT_DETECTED'; payload: Conflict }
  | { type: 'CONFLICT_RESOLVED'; payload: { taskId: string, resolution: 'keep_local' | 'use_remote' | 'merge' } };
```

### 状态更新流程
1. **本地操作**: 用户拖拽/创建任务 → 生成本地动作 → 立即更新UI（乐观更新）
2. **事件广播**: 通过WebSocket向服务器发送动作事件
3. **冲突检测**: 服务器广播事件到达时，检查本地版本与远程版本的差异
4. **冲突解决**: 如检测到冲突，暂停相关任务状态更新，显示冲突解决界面

## 关键实现方案

### HTML5原生拖拽实现
1. **拖拽数据设置**: 在`onDragStart`中设置`dataTransfer.setData('application/json', JSON.stringify(taskData))`
2. **拖拽效果控制**: 通过`dataTransfer.effectAllowed`和`dropEffect`控制移动/复制行为
3. **放置区域处理**: 使用`onDragOver`阻止默认行为，`onDrop`处理放置逻辑
4. **视觉反馈**: 通过CSS类名控制拖拽过程中的视觉状态变化

### 乐观更新策略
1. **立即响应**: 用户操作后立即更新UI，无需等待服务器确认
2. **本地版本控制**: 每个任务维护版本号，用于冲突检测
3. **回滚机制**: 服务器拒绝变更时（如版本冲突），回滚到服务器确认的状态
4. **同步队列**: 将待同步操作排队，确保操作顺序与服务器一致

### WebSocket模拟实现
1. **事件模拟器**: 创建`MockWebSocket`类，模拟WebSocket API
2. **随机延迟**: 模拟网络延迟（50-300ms）
3. **并发冲突模拟**: 随机模拟其他用户并发操作
4. **离线恢复**: 模拟网络断开和重新连接场景

### 冲突解决机制
1. **自动检测**: 比较本地版本和远程版本的时间戳和内容差异
2. **用户决策**: 当检测到冲突时，显示冲突详情供用户选择：
   - 保留本地修改
   - 使用远程修改
   - 手动合并修改
3. **版本合并**: 提供简单的三窗格合并界面（本地/远程/合并结果）

## Constraint Acknowledgment

### [L]TS - TypeScript语言
- 设计中的所有接口和类型都严格使用TypeScript语法
- 提供完整的类型安全，减少运行时错误
- 所有组件都有明确的Props类型定义

### [F]React - React框架
- 采用React 18+版本，使用函数组件和Hooks
- 充分利用React的声明式编程模型
- 组件设计遵循React最佳实践

### [Y]CSS_MODULES - CSS Modules样式方案
- 为每个组件创建独立的`.module.css`文件
- 类名局部作用域，避免全局样式污染
- 支持CSS变量和伪类选择器

### [!Y]NO_TW - 禁止Tailwind CSS
- 完全不使用Tailwind CSS类名
- 所有样式通过CSS Modules自定义编写
- 避免任何与Tailwind相关的工具或配置

### [!D]NO_DND_LIB - 禁止第三方拖拽库
- 完全不引入`react-dnd`、`react-beautiful-dnd`等库
- 仅使用HTML5原生拖拽API实现所有拖拽功能
- 手动处理所有拖拽事件和数据传输

### [DRAG]HTML5 - 使用HTML5原生拖拽
- 严格遵循HTML5拖拽API规范
- 使用`draggable="true"`、`ondragstart`、`ondragover`、`ondrop`等原生属性
- 通过`dataTransfer`对象传输任务数据

### [STATE]useReducer - 使用useReducer状态管理
- 将所有状态更新逻辑集中在Reducer函数中
- 确保状态变更的可预测性和可测试性
- 提供纯函数式的状态更新

### [O]SFC - 输出为单文件组件
- 每个组件在一个独立的`.tsx`文件中实现
- 组件文件包含所有相关逻辑（状态、效果、事件处理）
- 遵循单一职责原则

### [EXP]DEFAULT - 使用默认导出
- 每个组件文件使用`export default`语法
- 简化导入语句，提高代码可读性
- 符合React社区惯例

### [WS]MOCK - WebSocket使用模拟实现
- 不依赖真实WebSocket服务器
- 提供完整的本地模拟实现
- 支持开发者在不连接服务器的情况下测试协作功能

### [!D]NO_SOCKETIO - 禁止Socket.io库
- 完全不引入Socket.io客户端库
- 使用原生的WebSocket API或模拟实现
- 避免任何Socket.io特定的功能或模式

## 技术要点总结

1. **性能优化**: 使用React.memo优化组件重渲染，避免不必要的更新
2. **错误边界**: 实现React错误边界，防止组件崩溃影响整个应用
3. **可访问性**: 确保拖拽操作支持键盘导航和屏幕阅读器
4. **本地存储**: 使用IndexedDB或localStorage实现离线缓存
5. **测试策略**: 单元测试覆盖Reducer函数，集成测试验证组件交互

该设计方案严格遵守所有Header约束，同时满足用户需求中的实时协作、拖拽排序、乐观更新和冲突解决等核心功能。