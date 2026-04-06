# MC-FE-02: 虚拟滚动数据网格技术方案

## 1. 组件架构

### 1.1 核心组件
- **VirtualScrollGrid**: 主容器组件，管理虚拟滚动和渲染
- **GridHeader**: 固定表头组件，支持排序
- **GridRow**: 行渲染组件，虚拟化渲染
- **ScrollContainer**: 滚动容器组件，计算可见范围
- **SearchFilter**: 搜索过滤组件

### 1.2 组件职责
- **VirtualScrollGrid**: 协调虚拟滚动、数据管理和渲染
- **GridHeader**: 渲染固定表头，处理列排序点击事件
- **GridRow**: 渲染单个数据行，复用DOM元素
- **ScrollContainer**: 监听滚动事件，计算可见行索引
- **SearchFilter**: 提供搜索输入框，触发过滤逻辑

## 2. 虚拟滚动算法

### 2.1 可见范围计算
```
可视行数 = Math.ceil(容器高度 / 行高度)
起始索引 = Math.floor(滚动位置 / 行高度)
结束索引 = 起始索引 + 可视行数 + 缓冲行数
```

### 2.2 渲染优化策略
- **视口缓冲**: 渲染当前视口上下各10行作为缓冲
- **DOM复用**: 使用key属性复用行DOM元素
- **分批渲染**: 大量数据更新时分批渲染避免阻塞
- **请求动画帧**: 使用requestAnimationFrame进行滚动渲染

### 2.3 滚动位置同步
- **滚动事件节流**: 使用requestAnimationFrame节流滚动事件
- **位置预测**: 根据滚动速度预测下一帧位置
- **平滑滚动**: 实现惯性滚动效果
- **滚动条同步**: 保持滚动条位置与实际内容同步

## 3. 数据模型

```typescript
interface DataRow {
  id: string | number;
  [key: string]: any; // 动态列数据
}

interface ColumnDef {
  id: string;
  title: string;
  width: number;
  sortable: boolean;
  sortDirection?: 'asc' | 'desc' | null;
  filterable?: boolean;
  renderer?: (value: any, row: DataRow) => React.ReactNode;
}

interface GridState {
  data: DataRow[]; // 原始数据
  filteredData: DataRow[]; // 过滤后数据
  visibleData: DataRow[]; // 当前可见数据
  columns: ColumnDef[];
  sortColumn: string | null;
  sortDirection: 'asc' | 'desc' | null;
  searchTerm: string;
  scrollTop: number;
  rowHeight: number;
  containerHeight: number;
  visibleStart: number;
  visibleEnd: number;
  bufferSize: number;
}

interface RenderRange {
  start: number;
  end: number;
  total: number;
}
```

## 4. 排序和过滤方法

### 4.1 排序算法
- **多列排序**: 支持点击表头切换排序方向
- **稳定排序**: 保持相同值元素的相对顺序
- **类型感知**: 根据数据类型（字符串、数字、日期）选择排序策略
- **性能优化**: 对已排序数据避免重复排序

### 4.2 过滤实现
- **全文搜索**: 对所有列进行子字符串匹配
- **列级过滤**: 支持按列过滤（需扩展ColumnDef）
- **实时过滤**: 输入时实时更新过滤结果
- **防抖处理**: 搜索输入使用防抖避免频繁过滤

### 4.3 数据更新策略
- **增量更新**: 新数据到达时增量更新可见行
- **脏检查**: 标记需要更新的行，避免全量重绘
- **异步加载**: 支持滚动到底部时异步加载更多数据
- **数据切片**: 将大数据集切片处理

## 5. 约束确认

### 5.1 TS + React
- TypeScript定义数据模型和组件props
- React函数组件配合hooks
- 完整的类型安全保证

### 5.2 Manual virtual scroll, no react-window
- 手动实现虚拟滚动算法
- 计算可见范围和缓冲区域
- 管理DOM元素复用
- 实现滚动事件处理

### 5.3 CSS Modules, no Tailwind/inline
- 为每个组件创建CSS Modules样式文件
- 使用CSS类名控制样式
- 避免内联样式和Tailwind类名

### 5.4 No external deps
- 不使用任何第三方库
- 所有功能原生实现
- 仅依赖React和TypeScript

### 5.5 Single file, export default
- 所有代码在单个.tsx文件中
- 使用export default VirtualScrollGrid
- 内部模块化组织代码

### 5.6 Inline mock data
- 在组件内部生成10000行模拟数据
- 使用伪随机算法创建多样数据
- 包含不同类型（字符串、数字、日期）的列数据
- 数据生成逻辑包含在组件文件中