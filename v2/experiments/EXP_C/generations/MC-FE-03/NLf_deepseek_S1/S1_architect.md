# MC-FE-03: Canvas绘图白板技术方案

## 1. 组件架构

### 1.1 主要组件
- **CanvasWhiteboard**: 主组件，管理Canvas绘制和状态
- **Toolbar**: 工具栏组件，包含绘图工具选择
- **ColorPicker**: 颜色选择器组件
- **CanvasLayer**: Canvas渲染层组件
- **HistoryControls**: 撤销/重做控制组件

### 1.2 组件职责
- **CanvasWhiteboard**: 管理整体状态、协调子组件、处理键盘快捷键
- **Toolbar**: 提供工具选择（画笔、橡皮擦、清空）、显示当前工具状态
- **ColorPicker**: 提供颜色选择功能、显示当前颜色
- **CanvasLayer**: 负责Canvas元素的渲染、处理鼠标事件、执行绘制操作
- **HistoryControls**: 提供撤销/重做按钮、显示历史状态

## 2. Canvas绘制方法

### 2.1 事件流设计
```typescript
interface DrawingEventFlow {
  // 鼠标按下：开始新路径
  mousedown: (e: MouseEvent) => void;
  
  // 鼠标移动：绘制路径
  mousemove: (e: MouseEvent) => void;
  
  // 鼠标抬起：结束路径
  mouseup: (e: MouseEvent) => void;
  
  // 鼠标离开：取消绘制
  mouseleave: (e: MouseEvent) => void;
}
```

### 2.2 绘制流程
1. **事件监听**: 在Canvas元素上监听鼠标事件
2. **坐标转换**: 将页面坐标转换为Canvas坐标
3. **路径记录**: 记录鼠标移动形成的路径点
4. **实时绘制**: 在mousemove时实时绘制路径
5. **最终提交**: 在mouseup时将路径提交到状态

### 2.3 Canvas 2D API使用
- **getContext('2d')**: 获取2D绘图上下文
- **beginPath() / closePath()**: 路径管理
- **moveTo() / lineTo()**: 路径绘制
- **stroke() / fill()**: 路径渲染
- **clearRect()**: 清空画布区域
- **save() / restore()**: 状态保存/恢复

## 3. useReducer状态模型

### 3.1 状态结构
```typescript
interface DrawingState {
  // 当前绘制状态
  tool: 'pen' | 'eraser';
  color: string;
  lineWidth: number;
  
  // 绘制数据
  paths: DrawingPath[];
  currentPath: DrawingPath | null;
  
  // 历史管理
  history: DrawingState[];
  historyIndex: number;
  maxHistorySize: number;
  
  // Canvas状态
  canvasSize: { width: number; height: number };
  isDrawing: boolean;
}

interface DrawingPath {
  id: string;
  tool: 'pen' | 'eraser';
  color: string;
  lineWidth: number;
  points: Point[];
  timestamp: number;
}

interface Point {
  x: number;
  y: number;
  pressure?: number; // 压力感应支持
}
```

### 3.2 Action类型
```typescript
type Action =
  | { type: 'SET_TOOL'; payload: 'pen' | 'eraser' }
  | { type: 'SET_COLOR'; payload: string }
  | { type: 'SET_LINE_WIDTH'; payload: number }
  | { type: 'START_DRAWING'; payload: Point }
  | { type: 'ADD_POINT'; payload: Point }
  | { type: 'END_DRAWING' }
  | { type: 'CLEAR_CANVAS' }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'SAVE_TO_HISTORY' }
  | { type: 'RESTORE_FROM_HISTORY'; payload: number };
```

### 3.3 Reducer设计
- **纯函数**: 所有状态更新都是纯函数
- **不可变更新**: 使用展开运算符创建新状态
- **历史管理**: 自动保存状态到历史栈
- **边界检查**: 检查历史索引边界

## 4. 撤销/重做栈设计

### 4.1 历史栈结构
```typescript
interface HistoryStack {
  states: DrawingState[];
  currentIndex: number;
  capacity: number;
}

// 历史操作方法
interface HistoryOperations {
  push(state: DrawingState): void;
  undo(): DrawingState | null;
  redo(): DrawingState | null;
  canUndo(): boolean;
  canRedo(): boolean;
  clear(): void;
}
```

### 4.2 实现策略
1. **快照保存**: 每次重要操作后保存完整状态快照
2. **增量保存**: 对于连续绘制，保存路径增量
3. **内存优化**: 限制历史栈大小（默认50步）
4. **序列化优化**: 使用JSON序列化/反序列化

### 4.3 撤销/重做流程
1. **撤销**: 
   - 检查canUndo()
   - 从历史栈获取前一个状态
   - 恢复Canvas到该状态
   - 重新渲染所有路径

2. **重做**:
   - 检查canRedo()
   - 从历史栈获取下一个状态
   - 恢复Canvas到该状态
   - 重新渲染所有路径

## 5. 约束确认

### 约束1: TypeScript + React框架
- 使用TypeScript进行类型安全开发
- 使用React函数组件和Hooks
- 所有组件都有完整的TypeScript接口定义

### 约束2: 原生Canvas 2D API
- 使用getContext('2d')获取绘图上下文
- 实现完整的路径绘制逻辑
- 不使用fabric.js、konva等Canvas库

### 约束3: 完全使用useReducer
- 所有状态通过useReducer管理
- 不使用useState Hook
- 定义完整的action类型和reducer

### 约束4: 无外部npm包
- 仅使用React和TypeScript
- 所有Canvas功能手动实现
- 不引入任何第三方库

### 约束5: 单文件导出
- 所有代码在一个.tsx文件中
- 使用export default导出CanvasWhiteboard组件
- 组件内部定义所有子组件

### 约束6: 仅输出代码
- 文档只描述设计，不包含实现代码
- 最终实现将只包含纯TypeScript/React代码
- 无解释性注释

## 6. 关键实现细节

### 6.1 性能优化
1. **离屏Canvas**: 使用离屏Canvas进行复杂绘制
2. **路径简化**: 使用Ramer-Douglas-Peucker算法简化路径
3. **脏矩形渲染**: 只重绘发生变化区域
4. **防抖渲染**: 使用requestAnimationFrame节流渲染

### 6.2 功能实现
1. **画笔工具**: 
   - 实现平滑曲线绘制
   - 支持压力感应（如果设备支持）
   - 可配置线宽和颜色

2. **橡皮擦工具**:
   - 使用destination-out合成模式
   - 支持不同大小橡皮擦
   - 实现擦除路径记录

3. **颜色选择器**:
   - 预定义颜色调色板
   - 支持自定义颜色输入
   - 显示当前选择颜色

### 6.3 用户体验
1. **键盘快捷键**:
   - Ctrl+Z: 撤销
   - Ctrl+Y: 重做
   - Ctrl+C: 清空画布
   - B: 切换画笔
   - E: 切换橡皮擦

2. **视觉反馈**:
   - 光标形状随工具变化
   - 绘制时显示预览线
   - 工具状态高亮显示

3. **响应式设计**:
   - Canvas随窗口大小调整
   - 工具栏自适应布局
   - 触摸设备支持

## 7. 扩展功能预留

1. **图层系统**: 支持多个绘制图层
2. **形状工具**: 添加矩形、圆形、直线等形状
3. **文本工具**: 支持在Canvas上添加文本
4. **图像导入**: 支持导入图片作为背景
5. **导出功能**: 支持PNG、JPEG格式导出
6. **协作绘制**: 可扩展为实时协作白板

## 8. 测试考虑

1. **单元测试**: 测试reducer函数
2. **集成测试**: 测试Canvas绘制流程
3. **性能测试**: 测试大量路径的渲染性能
4. **兼容性测试**: 测试不同浏览器和设备的兼容性

---

*文档字数: 约1950字*