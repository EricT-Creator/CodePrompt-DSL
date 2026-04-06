# MC-FE-03: Canvas绘图白板技术方案

## 1. 组件架构

### 1.1 核心组件
- **CanvasWhiteboard**: 主容器组件，管理Canvas和工具状态
- **Toolbar**: 工具栏组件，包含画笔、橡皮擦、颜色选择器
- **CanvasLayer**: Canvas渲染层组件，处理绘图逻辑
- **HistoryManager**: 历史记录管理组件
- **ColorPicker**: 颜色选择器组件

### 1.2 组件职责
- **CanvasWhiteboard**: 协调所有子组件，管理应用状态
- **Toolbar**: 提供工具切换按钮，显示当前工具状态
- **CanvasLayer**: 渲染Canvas，处理鼠标事件，执行绘图操作
- **HistoryManager**: 管理撤销/重做栈，控制历史状态
- **ColorPicker**: 显示颜色选择界面，更新画笔颜色

## 2. Canvas绘制方法

### 2.1 事件流设计
```
mousedown → 开始新路径/橡皮擦操作
mousemove → 记录路径点/更新橡皮擦位置
mouseup → 完成当前操作，保存到历史栈
mouseleave → 中断当前操作
```

### 2.2 绘图上下文管理
- **双缓冲技术**: 使用离屏Canvas进行绘制，再复制到主Canvas
- **路径优化**: 使用`lineTo()`连接点，减少绘制调用
- **状态保存**: 使用`save()`和`restore()`管理绘图状态
- **性能优化**: 批量绘制操作，减少重绘次数

### 2.3 工具实现方法
- **画笔工具**: 记录路径点，使用`quadraticCurveTo()`平滑曲线
- **橡皮擦工具**: 使用`globalCompositeOperation = 'destination-out'`
- **颜色选择器**: 使用`input[type="color"]`或自定义颜色选择
- **清除画布**: 使用`clearRect()`清空整个Canvas

## 3. 状态模型设计

### 3.1 useReducer状态结构
```typescript
interface CanvasState {
  tool: 'pen' | 'eraser' | 'clear';
  color: string;
  lineWidth: number;
  isDrawing: boolean;
  currentPath: Point[];
  history: CanvasSnapshot[];
  historyIndex: number;
  canvasSize: { width: number; height: number };
}

interface Point {
  x: number;
  y: number;
  pressure?: number;
  timestamp: number;
}

interface CanvasSnapshot {
  id: string;
  timestamp: number;
  dataUrl?: string; // 用于快速恢复
  commands?: DrawCommand[]; // 命令式恢复
}

interface DrawCommand {
  type: 'pen' | 'eraser' | 'clear';
  points: Point[];
  color?: string;
  lineWidth?: number;
}
```

### 3.2 Action类型
```typescript
type CanvasAction =
  | { type: 'SET_TOOL'; payload: 'pen' | 'eraser' | 'clear' }
  | { type: 'SET_COLOR'; payload: string }
  | { type: 'SET_LINE_WIDTH'; payload: number }
  | { type: 'START_DRAWING'; payload: Point }
  | { type: 'ADD_POINT'; payload: Point }
  | { type: 'STOP_DRAWING' }
  | { type: 'CLEAR_CANVAS' }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'SAVE_SNAPSHOT' }
  | { type: 'RESTORE_SNAPSHOT'; payload: number };
```

### 3.3 Reducer设计原则
- **纯函数**: 不产生副作用，仅根据action更新state
- **不可变性**: 使用展开运算符创建新state对象
- **命令合并**: 将连续的点添加合并为单个路径更新
- **快照优化**: 定期保存Canvas快照，避免命令重放开销

## 4. 撤销/重做栈设计

### 4.1 历史记录策略
- **增量快照**: 每次绘图操作完成后保存Canvas状态
- **命令记录**: 同时保存绘制命令用于精确恢复
- **内存优化**: 限制历史栈大小（如最多50步）
- **状态压缩**: 对相似状态进行压缩存储

### 4.2 撤销/重做实现
- **栈结构**: 使用数组存储历史状态，指针跟踪当前位置
- **增量恢复**: 从最近快照应用/撤销命令，而非全量重绘
- **状态恢复**: 使用`putImageData()`快速恢复Canvas状态
- **边界处理**: 处理栈底/栈顶边界条件

### 4.3 性能优化
- **延迟快照**: 高频绘图时延迟快照保存
- **批量操作**: 将多个点合并为单个历史条目
- **内存管理**: 定期清理过时快照
- **Canvas状态缓存**: 缓存常用绘图状态

## 5. 约束确认

### 5.1 TS + React
- TypeScript定义所有Canvas相关类型
- React函数组件配合useReducer
- 类型安全的绘图命令和状态管理

### 5.2 Native Canvas 2D, no fabric/konva
- 使用原生Canvas 2D API
- 手动实现所有绘图工具
- 不依赖任何Canvas框架或库

### 5.3 useReducer only, no useState
- 单一useReducer管理所有状态
- 定义完整的action类型系统
- 通过dispatch函数统一状态更新

### 5.4 No external deps
- 不使用任何第三方库
- 原生实现所有Canvas功能和UI组件
- 仅依赖React和TypeScript

### 5.5 Single file, export default
- 所有代码在单个.tsx文件中
- 使用export default CanvasWhiteboard
- 内部模块化组织Canvas工具和组件

### 5.6 Code only
- 不包含任何外部资源
- 所有绘图逻辑用代码实现
- 颜色选择器使用原生HTML5 input或手动实现