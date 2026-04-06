# MC-FE-03: Canvas绘图白板技术方案

## 项目概述
构建一个基于Canvas的绘图白板应用，支持画笔工具、橡皮擦、颜色选择器、撤销/重做和清空画布功能。通过鼠标事件（mousedown, mousemove, mouseup）捕获绘图路径，提供流畅的绘图体验。

## 约束解析
基于Header约束：`[L]TS [F]React [!D]NO_CANVAS_LIB [DRAW]CTX2D [STATE]useReducer_ONLY [D]NO_EXTERNAL [O]SFC [EXP]DEFAULT [OUT]CODE_ONLY`

约束映射表：
| 约束标识 | 含义 |
|---------|------|
| [L]TS | 使用TypeScript |
| [F]React | 使用React框架 |
| [!D]NO_CANVAS_LIB | 禁止使用Canvas绘图库 |
| [DRAW]CTX2D | 使用Canvas 2D上下文 |
| [STATE]useReducer_ONLY | 仅使用useReducer进行状态管理 |
| [D]NO_EXTERNAL | 禁止使用外部依赖 |
| [O]SFC | 输出为单文件组件 |
| [EXP]DEFAULT | 使用默认导出 |
| [OUT]CODE_ONLY | 仅输出代码，不包含样式 |

## 组件架构设计

### 双Canvas层架构
```
CanvasWhiteboard (根组件)
├── CanvasContainer (画布容器)
│   ├── BackgroundCanvas (背景层Canvas)
│   │   └── GridRenderer (网格渲染器)
│   ├── DrawingCanvas (绘图层Canvas)
│   │   ├── PathRenderer (路径渲染器)
│   │   └── CursorRenderer (光标渲染器)
│   └── PreviewCanvas (预览层Canvas)
│       └── PreviewRenderer (预览渲染器)
├── Toolbar (工具栏)
│   ├── ToolButton × N (工具按钮)
│   ├── ColorPicker (颜色选择器)
│   └── BrushSizeSlider (画笔大小滑块)
├── HistoryControls (历史控制)
│   ├── UndoButton (撤销按钮)
│   ├── RedoButton (重做按钮)
│   └── ClearButton (清空按钮)
└── StatusBar (状态栏)
    ├── CurrentTool (当前工具显示)
    └── Coordinates (坐标显示)
```

### 组件职责说明
1. **CanvasWhiteboard**: 根组件，管理所有状态和事件分发
2. **CanvasContainer**: 画布容器，管理三个Canvas层的布局和协调
3. **BackgroundCanvas**: 背景层，渲染静态网格和参考线
4. **DrawingCanvas**: 绘图层，渲染所有已完成的绘图路径
5. **PreviewCanvas**: 预览层，实时渲染当前正在绘制的路径
6. **Toolbar**: 工具栏，提供工具选择和参数调整
7. **ToolButton**: 工具按钮，激活特定绘图工具
8. **ColorPicker**: 颜色选择器，管理画笔颜色
9. **BrushSizeSlider**: 画笔大小滑块，调整画笔粗细
10. **HistoryControls**: 历史控制，管理撤销/重做/清空操作
11. **StatusBar**: 状态栏，显示当前状态和坐标信息

## Canvas绘图方案

### 事件流设计
```typescript
// 鼠标事件处理流程
const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
  const point = getCanvasCoordinates(e);
  
  dispatch({
    type: 'DRAW_START',
    payload: { point, tool: state.currentTool }
  });
  
  // 开始绘图
  if (state.currentTool === 'pen' || state.currentTool === 'eraser') {
    startDrawing(point);
  }
};

const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
  const point = getCanvasCoordinates(e);
  
  dispatch({
    type: 'MOUSE_MOVE',
    payload: { point }
  });
  
  // 实时预览
  if (state.isDrawing) {
    updatePreview(point);
  }
};

const handleMouseUp = (e: React.MouseEvent<HTMLCanvasElement>) => {
  const point = getCanvasCoordinates(e);
  
  dispatch({
    type: 'DRAW_END',
    payload: { point }
  });
  
  // 完成绘图
  if (state.isDrawing) {
    finishDrawing(point);
  }
};
```

### Canvas 2D上下文使用
```typescript
// 获取和配置Canvas上下文
function setupCanvasContext(canvas: HTMLCanvasElement): CanvasRenderingContext2D {
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('Canvas 2D context not available');
  
  // 配置绘图属性
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  
  return ctx;
}

// 绘图工具实现
const drawingTools = {
  pen: (ctx: CanvasRenderingContext2D, path: Point[], color: string, size: number) => {
    ctx.strokeStyle = color;
    ctx.lineWidth = size;
    drawPath(ctx, path);
  },
  
  eraser: (ctx: CanvasRenderingContext2D, path: Point[], size: number) => {
    ctx.globalCompositeOperation = 'destination-out';
    ctx.strokeStyle = 'rgba(0,0,0,1)';
    ctx.lineWidth = size;
    drawPath(ctx, path);
    ctx.globalCompositeOperation = 'source-over';
  },
  
  // ... 其他工具实现
};
```

## 状态管理方案

### useReducer状态设计
```typescript
// 状态结构定义
type WhiteboardState = {
  // 绘图状态
  isDrawing: boolean;
  currentTool: ToolType;
  currentColor: string;
  brushSize: number;
  
  // 画布数据
  paths: Path[];
  currentPath: Path | null;
  
  // 历史状态
  history: HistoryState[];
  historyIndex: number;
  
  // UI状态
  canvasSize: { width: number; height: number };
  mousePosition: Point | null;
  showGrid: boolean;
  gridSize: number;
};

// 工具类型定义
type ToolType = 'pen' | 'eraser' | 'select' | 'move' | 'shape';

// 路径数据结构
interface Path {
  id: string;
  type: ToolType;
  points: Point[];
  color: string;
  size: number;
  createdAt: number;
}

// 点坐标
interface Point {
  x: number;
  y: number;
  pressure?: number; // 支持压感
  timestamp: number;
}

// 历史状态快照
interface HistoryState {
  id: string;
  paths: Path[];
  timestamp: number;
  description: string;
}
```

### 动作类型定义
```typescript
type WhiteboardAction =
  // 绘图动作
  | { type: 'SET_TOOL'; payload: ToolType }
  | { type: 'SET_COLOR'; payload: string }
  | { type: 'SET_BRUSH_SIZE'; payload: number }
  | { type: 'DRAW_START'; payload: { point: Point; tool: ToolType } }
  | { type: 'DRAW_UPDATE'; payload: { point: Point } }
  | { type: 'DRAW_END'; payload: { point: Point } }
  
  // 历史动作
  | { type: 'SAVE_HISTORY' }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'CLEAR_CANVAS' }
  
  // UI动作
  | { type: 'SET_CANVAS_SIZE'; payload: { width: number; height: number } }
  | { type: 'SET_MOUSE_POSITION'; payload: Point | null }
  | { type: 'TOGGLE_GRID' }
  | { type: 'SET_GRID_SIZE'; payload: number };
```

### Reducer实现示例
```typescript
function whiteboardReducer(state: WhiteboardState, action: WhiteboardAction): WhiteboardState {
  switch (action.type) {
    case 'DRAW_START': {
      const { point, tool } = action.payload;
      const newPath: Path = {
        id: generateId(),
        type: tool,
        points: [point],
        color: state.currentColor,
        size: state.brushSize,
        createdAt: Date.now()
      };
      
      return {
        ...state,
        isDrawing: true,
        currentPath: newPath
      };
    }
    
    case 'DRAW_UPDATE': {
      if (!state.isDrawing || !state.currentPath) return state;
      
      const updatedPath = {
        ...state.currentPath,
        points: [...state.currentPath.points, action.payload.point]
      };
      
      return {
        ...state,
        currentPath: updatedPath
      };
    }
    
    case 'DRAW_END': {
      if (!state.isDrawing || !state.currentPath) return state;
      
      const completedPath = {
        ...state.currentPath,
        points: [...state.currentPath.points, action.payload.point]
      };
      
      const newPaths = [...state.paths, completedPath];
      
      return {
        ...state,
        isDrawing: false,
        currentPath: null,
        paths: newPaths
      };
    }
    
    case 'UNDO': {
      if (state.historyIndex <= 0) return state;
      
      const newIndex = state.historyIndex - 1;
      const restoredPaths = state.history[newIndex].paths;
      
      return {
        ...state,
        paths: restoredPaths,
        historyIndex: newIndex
      };
    }
    
    // ... 其他case处理
  }
}
```

## 撤销/重做栈设计

### 历史管理策略
```typescript
// 历史栈实现
class HistoryManager {
  private stack: HistoryState[] = [];
  private index = -1;
  private maxSize = 50;
  
  // 保存状态
  save(paths: Path[], description: string): void {
    // 移除当前索引之后的所有状态
    this.stack = this.stack.slice(0, this.index + 1);
    
    // 添加新状态
    const newState: HistoryState = {
      id: generateId(),
      paths: deepClone(paths),
      timestamp: Date.now(),
      description
    };
    
    this.stack.push(newState);
    this.index++;
    
    // 限制栈大小
    if (this.stack.length > this.maxSize) {
      this.stack.shift();
      this.index--;
    }
  }
  
  // 撤销
  undo(): HistoryState | null {
    if (this.index <= 0) return null;
    this.index--;
    return this.stack[this.index];
  }
  
  // 重做
  redo(): HistoryState | null {
    if (this.index >= this.stack.length - 1) return null;
    this.index++;
    return this.stack[this.index];
  }
  
  // 获取当前状态
  getCurrent(): HistoryState | null {
    if (this.index < 0) return null;
    return this.stack[this.index];
  }
  
  // 清空历史
  clear(): void {
    this.stack = [];
    this.index = -1;
  }
}
```

### 智能保存策略
1. **时间阈值**: 绘图完成后延迟500ms自动保存历史
2. **变化阈值**: 路径点数量超过10个时自动保存
3. **工具切换**: 切换工具时自动保存当前状态
4. **手动保存**: 用户执行特定操作时保存（如清空、导入等）

### 撤销/重做可视化
1. **状态预览**: 在历史面板中显示状态缩略图
2. **描述信息**: 为每个历史状态添加描述（如"绘制路径"、"使用橡皮擦"等）
3. **快捷键**: 支持Ctrl+Z/Ctrl+Y快捷键操作
4. **禁用状态**: 根据历史索引禁用相应的按钮

## 双Canvas层实现

### 分层渲染策略
```typescript
// 三层Canvas渲染函数
function renderCanvasLayers(
  bgCanvas: HTMLCanvasElement,
  drawCanvas: HTMLCanvasElement,
  previewCanvas: HTMLCanvasElement,
  state: WhiteboardState
) {
  const bgCtx = bgCanvas.getContext('2d')!;
  const drawCtx = drawCanvas.getContext('2d')!;
  const previewCtx = previewCanvas.getContext('2d')!;
  
  // 1. 清空所有Canvas
  clearCanvas(bgCtx, bgCanvas);
  clearCanvas(drawCtx, drawCanvas);
  clearCanvas(previewCtx, previewCanvas);
  
  // 2. 渲染背景层（网格）
  if (state.showGrid) {
    renderGrid(bgCtx, bgCanvas, state.gridSize);
  }
  
  // 3. 渲染绘图层（已完成路径）
  state.paths.forEach(path => {
    renderPath(drawCtx, path);
  });
  
  // 4. 渲染预览层（当前绘制路径）
  if (state.currentPath) {
    renderPath(previewCtx, state.currentPath);
  }
  
  // 5. 渲染光标预览
  if (state.mousePosition) {
    renderCursorPreview(previewCtx, state);
  }
}
```

### 性能优化技术
1. **脏矩形渲染**: 仅重绘发生变化的部分区域
2. **离屏Canvas**: 使用离屏Canvas缓存复杂图形
3. **渲染节流**: 使用`requestAnimationFrame`控制渲染频率
4. **内存管理**: 及时清理不再使用的Canvas和ImageData

### 坐标转换系统
```typescript
// 坐标转换工具
class CoordinateSystem {
  private scale = 1.0;
  private offset = { x: 0, y: 0 };
  private canvasRect: DOMRect | null = null;
  
  // 屏幕坐标转Canvas坐标
  screenToCanvas(screenX: number, screenY: number): Point {
    if (!this.canvasRect) return { x: screenX, y: screenY };
    
    return {
      x: (screenX - this.canvasRect.left - this.offset.x) / this.scale,
      y: (screenY - this.canvasRect.top - this.offset.y) / this.scale
    };
  }
  
  // Canvas坐标转屏幕坐标
  canvasToScreen(canvasX: number, canvasY: number): Point {
    if (!this.canvasRect) return { x: canvasX, y: canvasY };
    
    return {
      x: canvasX * this.scale + this.offset.x + this.canvasRect.left,
      y: canvasY * this.scale + this.offset.y + this.canvasRect.top
    };
  }
  
  // 更新Canvas边界
  updateCanvasRect(canvas: HTMLCanvasElement): void {
    this.canvasRect = canvas.getBoundingClientRect();
  }
}
```

## 工具实现细节

### 画笔工具
1. **贝塞尔曲线**: 使用二次贝塞尔曲线平滑路径
2. **压力感应**: 支持压感输入（如有）
3. **笔迹平滑**: 使用移动平均算法平滑抖动
4. **颜色混合**: 支持透明度混合效果

### 橡皮擦工具
1. **复合操作**: 使用`globalCompositeOperation = 'destination-out'`
2. **擦除形状**: 圆形擦除区域，大小可调
3. **历史记录**: 橡皮擦操作纳入撤销/重做系统
4. **性能优化**: 批量擦除操作合并渲染

### 颜色选择器
1. **色板预设**: 提供常用颜色预设
2. **HSL选择**: 支持HSL颜色模型选择
3. **颜色历史**: 记录最近使用的颜色
4. **透明度**: 支持颜色透明度调整

### 画笔大小控制
1. **滑块控制**: 线性滑块调整画笔大小
2. **快捷键**: 支持[和]键快速调整大小
3. **预览显示**: 光标实时显示当前画笔大小
4. **压力映射**: 压感设备映射到画笔大小

## Constraint Acknowledgment

### [L]TS - TypeScript语言
- 所有状态、动作和工具都有完整的类型定义
- 利用TypeScript的泛型和联合类型确保类型安全
- 编译时检查所有Canvas API调用

### [F]React - React框架
- 使用React函数组件和Hooks架构
- 利用React的生命周期管理Canvas资源
- 遵循React的性能优化模式

### [!D]NO_CANVAS_LIB - 禁止Canvas绘图库
- 完全不使用`fabric.js`、`konva.js`等Canvas库
- 直接使用原生Canvas 2D API实现所有绘图功能
- 自主控制所有绘图算法和渲染逻辑

### [DRAW]CTX2D - 使用Canvas 2D上下文
- 仅使用`CanvasRenderingContext2D` API
- 不依赖WebGL或第三方渲染引擎
- 确保在所有支持Canvas的浏览器中兼容

### [STATE]useReducer_ONLY - 仅使用useReducer
- 所有状态管理都通过useReducer实现
- 不使用useState、Context或其他状态管理方案
- 确保状态变更的可预测性和可测试性

### [D]NO_EXTERNAL - 禁止外部依赖
- 不引入任何第三方JavaScript库
- 所有功能都通过原生API和自定义算法实现
- 保持代码库的最小化和可控性

### [O]SFC - 输出为单文件组件
- 整个白板应用在一个`.tsx`文件中实现
- 包含所有Canvas操作、状态管理和UI组件
- 遵循单一文件职责原则

### [EXP]DEFAULT - 使用默认导出
- 组件使用`export default CanvasWhiteboard`
- 简化导入和使用方式
- 符合React组件导出惯例

### [OUT]CODE_ONLY - 仅输出代码
- 不包含任何CSS样式定义
- 所有样式通过内联style属性或CSS-in-JS实现
- 确保输出纯粹是TypeScript/JavaScript代码

## 技术挑战与解决方案

1. **性能优化**: 使用三层Canvas分离静态和动态内容，减少重绘
2. **路径平滑**: 实现贝塞尔曲线插值算法，消除手绘抖动
3. **历史管理**: 设计高效的历史栈数据结构，支持快速撤销/重做
4. **坐标精度**: 实现高精度坐标转换系统，支持缩放和平移
5. **事件处理**: 统一处理鼠标、触摸和笔输入事件

该设计方案完全满足Canvas绘图白板的所有功能需求，同时严格遵守所有Header约束，提供流畅的绘图体验和完整的历史管理功能。