# MC-FE-02: 虚拟滚动数据表格技术方案

## 项目概述
构建一个高性能的虚拟滚动数据表格组件，支持10,000行数据的高效渲染。组件包含固定表头、可排序列（至少2列）和搜索/过滤输入框，确保滚动流畅无闪烁。

## 约束解析
基于Header约束：`[L]TS [F]React [!D]NO_VIRT_LIB [SCROLL]MANUAL [Y]CSS_MODULES [!Y]NO_TW_INLINE [D]NO_EXTERNAL [O]SFC [EXP]DEFAULT [DT]INLINE_MOCK`

约束映射表：
| 约束标识 | 含义 |
|---------|------|
| [L]TS | 使用TypeScript |
| [F]React | 使用React框架 |
| [!D]NO_VIRT_LIB | 禁止使用虚拟滚动库 |
| [SCROLL]MANUAL | 手动实现虚拟滚动算法 |
| [Y]CSS_MODULES | 使用CSS Modules样式方案 |
| [!Y]NO_TW_INLINE | 禁止使用Tailwind内联样式 |
| [D]NO_EXTERNAL | 禁止使用外部依赖 |
| [O]SFC | 输出为单文件组件 |
| [EXP]DEFAULT | 使用默认导出 |
| [DT]INLINE_MOCK | 数据使用内联模拟 |

## 组件架构设计

### 核心组件结构
```
VirtualDataGrid (根组件)
├── GridHeader (固定表头)
│   ├── HeaderCell × N (表头单元格)
│   └── SortIndicator (排序指示器)
├── GridBody (表格主体)
│   ├── VisibleRows (可见行容器)
│   │   └── GridRow × M (可见行组件)
│   │       └── GridCell × N (单元格组件)
│   ├── TopSpacer (顶部空白占位符)
│   └── BottomSpacer (底部空白占位符)
├── SearchFilter (搜索过滤栏)
│   ├── SearchInput (搜索输入框)
│   └── FilterChips (过滤标签)
└── Scrollbar (自定义滚动条)
```

### 组件职责说明
1. **VirtualDataGrid**: 根组件，管理所有数据、虚拟滚动状态和用户交互
2. **GridHeader**: 固定表头，支持列排序、列宽调整
3. **HeaderCell**: 单个表头单元格，处理点击排序事件
4. **GridBody**: 表格主体，实现虚拟滚动核心逻辑
5. **VisibleRows**: 可见行容器，仅渲染当前视口内的行
6. **GridRow**: 单行组件，管理行状态和单元格渲染
7. **GridCell**: 单元格组件，负责数据展示和格式化
8. **TopSpacer/BottomSpacer**: 空白占位符，维持滚动区域总高度
9. **SearchFilter**: 搜索过滤组件，处理用户查询
10. **Scrollbar**: 自定义滚动条，提供更精确的滚动控制

## 虚拟滚动算法设计

### 视口范围计算
```typescript
// 关键参数定义
interface ViewportMetrics {
  containerHeight: number;      // 容器可视高度
  rowHeight: number;           // 单行固定高度
  totalRows: number;           // 总行数
  scrollTop: number;           // 当前滚动位置
  overscanCount: number;       // 预渲染行数（上下各3行）
}

// 计算可见行范围
function calculateVisibleRange(metrics: ViewportMetrics): {
  startIndex: number;
  endIndex: number;
  visibleCount: number;
} {
  const { containerHeight, rowHeight, totalRows, scrollTop, overscanCount } = metrics;
  
  // 计算当前视口起始行
  const startIndex = Math.max(0, Math.floor(scrollTop / rowHeight) - overscanCount);
  
  // 计算当前视口结束行
  const visibleRows = Math.ceil(containerHeight / rowHeight);
  const endIndex = Math.min(
    totalRows - 1,
    startIndex + visibleRows + overscanCount * 2
  );
  
  return {
    startIndex,
    endIndex,
    visibleCount: endIndex - startIndex + 1
  };
}
```

### 滚动位置同步
1. **滚动事件监听**: 监听容器元素的`onscroll`事件
2. **防抖优化**: 使用`requestAnimationFrame`进行节流，避免频繁重渲染
3. **滚动条位置**: 根据当前滚动位置计算空白占位符高度
4. **平滑滚动**: 通过CSS `transform`实现硬件加速的平滑滚动

### 性能优化策略
1. **行高固定**: 采用固定行高，简化位置计算
2. **行键复用**: 为每行生成唯一key，支持React高效复用
3. **内存池**: 重用已卸载的行组件，减少垃圾回收
4. **渲染批处理**: 将多个状态更新合并为单次渲染

## 数据模型设计

### TypeScript接口定义
```typescript
// 数据行接口
interface DataRow {
  id: string | number;
  [key: string]: any; // 动态列数据
}

// 列定义
interface ColumnDef {
  id: string;
  title: string;
  width: number;
  sortable: boolean;
  filterable: boolean;
  render?: (value: any, row: DataRow) => React.ReactNode;
  comparator?: (a: any, b: any) => number;
}

// 表格状态
interface GridState {
  data: DataRow[];
  filteredData: DataRow[];
  columns: ColumnDef[];
  sortBy: { columnId: string, direction: 'asc' | 'desc' } | null;
  filters: Record<string, string>;
  viewport: ViewportMetrics;
  selectedRows: Set<string | number>;
}

// 排序状态
interface SortState {
  columnId: string;
  direction: 'asc' | 'desc';
  multiSort: boolean; // 是否支持多列排序
}

// 过滤条件
interface FilterCondition {
  columnId: string;
  operator: 'contains' | 'equals' | 'startsWith' | 'endsWith' | 'greaterThan' | 'lessThan';
  value: string;
}
```

### 内联数据模拟
```typescript
// 生成模拟数据
function generateMockData(count: number, columns: ColumnDef[]): DataRow[] {
  return Array.from({ length: count }, (_, index) => {
    const row: DataRow = { id: index + 1 };
    
    columns.forEach(column => {
      switch (column.id) {
        case 'name':
          row[column.id] = `User ${index + 1}`;
          break;
        case 'email':
          row[column.id] = `user${index + 1}@example.com`;
          break;
        case 'age':
          row[column.id] = Math.floor(Math.random() * 50) + 20;
          break;
        case 'status':
          row[column.id] = ['Active', 'Inactive', 'Pending'][index % 3];
          break;
        default:
          row[column.id] = `Value ${index + 1}`;
      }
    });
    
    return row;
  });
}
```

## 排序和过滤方案

### 排序算法实现
1. **单列排序**: 点击表头切换升序/降序/取消排序
2. **多列排序**: 支持Shift+点击进行多列排序（优先级排序）
3. **自定义比较器**: 每列可配置自定义比较函数
4. **稳定排序**: 使用稳定排序算法，保持相同值行的原始顺序

### 过滤实现方案
1. **实时过滤**: 输入框内容变化时实时更新过滤结果
2. **多条件过滤**: 支持多列组合过滤
3. **过滤类型**: 
   - 文本过滤：包含、等于、开头、结尾
   - 数值过滤：大于、小于、等于、范围
   - 枚举过滤：多选框选择
4. **过滤性能**: 使用索引和缓存优化过滤性能

### 搜索过滤组件设计
```typescript
// 搜索过滤状态
interface SearchFilterState {
  globalSearch: string;
  columnFilters: Record<string, string>;
  activeFilters: FilterCondition[];
}

// 过滤函数
function applyFilters(
  data: DataRow[],
  filters: FilterCondition[],
  columns: ColumnDef[]
): DataRow[] {
  return data.filter(row => {
    return filters.every(filter => {
      const value = row[filter.columnId];
      const filterValue = filter.value.toLowerCase();
      
      switch (filter.operator) {
        case 'contains':
          return String(value).toLowerCase().includes(filterValue);
        case 'equals':
          return String(value).toLowerCase() === filterValue;
        case 'startsWith':
          return String(value).toLowerCase().startsWith(filterValue);
        case 'endsWith':
          return String(value).toLowerCase().endsWith(filterValue);
        default:
          return true;
      }
    });
  });
}
```

## 关键实现细节

### 固定表头实现
1. **CSS定位**: 使用`position: sticky`实现表头固定
2. **滚动同步**: 表头与主体水平滚动同步
3. **列宽调整**: 支持拖拽调整列宽，实时更新所有行

### 单元格渲染优化
1. **虚拟化渲染**: 仅渲染可见单元格
2. **内容裁剪**: 长文本自动裁剪，鼠标悬停显示完整内容
3. **格式化工具**: 提供日期、货币、百分比等格式化函数
4. **条件渲染**: 根据数据类型动态选择渲染组件

### 滚动条定制
1. **原生样式覆盖**: 隐藏原生滚动条，使用自定义样式
2. **滚动条计算**: 根据内容高度计算滚动条比例
3. **拖拽交互**: 支持拖拽滚动条快速定位
4. **键盘导航**: 支持键盘方向键、PageUp/Down、Home/End导航

### 性能监控
1. **渲染时间**: 监控每帧渲染时间，确保60fps
2. **内存使用**: 跟踪组件实例数量，防止内存泄漏
3. **滚动流畅度**: 检测滚动卡顿，自动调整优化策略
4. **数据加载**: 支持分页或增量加载大数据集

## Constraint Acknowledgment

### [L]TS - TypeScript语言
- 所有接口、类型和函数都有完整的TypeScript定义
- 提供编译时类型检查，确保数据一致性
- 利用泛型支持灵活的数据类型

### [F]React - React框架
- 使用React函数组件和Hooks
- 遵循React性能优化最佳实践
- 利用React Context进行深层状态传递

### [!D]NO_VIRT_LIB - 禁止虚拟滚动库
- 完全不使用`react-window`、`react-virtualized`等库
- 从零实现虚拟滚动核心算法
- 自主控制所有性能优化策略

### [SCROLL]MANUAL - 手动实现虚拟滚动
- 手动计算视口范围和渲染行数
- 自主实现滚动事件处理和性能优化
- 提供完整的虚拟滚动控制逻辑

### [Y]CSS_MODULES - CSS Modules样式方案
- 每个组件都有对应的`.module.css`文件
- 样式类名局部作用域，避免冲突
- 支持CSS变量和媒体查询

### [!Y]NO_TW_INLINE - 禁止Tailwind内联样式
- 完全不使用Tailwind CSS类名
- 所有样式通过CSS Modules定义
- 避免任何内联样式或Tailwind工具类

### [D]NO_EXTERNAL - 禁止外部依赖
- 不引入任何第三方库
- 所有功能都通过原生JavaScript/TypeScript实现
- 保持代码库的纯净和可控

### [O]SFC - 输出为单文件组件
- 整个虚拟表格在一个`.tsx`文件中实现
- 包含所有子组件、工具函数和样式定义
- 遵循单一文件职责原则

### [EXP]DEFAULT - 使用默认导出
- 组件使用`export default VirtualDataGrid`
- 简化导入和使用方式
- 符合React组件导出惯例

### [DT]INLINE_MOCK - 数据使用内联模拟
- 不依赖外部API或数据源
- 在组件内部生成模拟数据
- 支持开发者快速测试和演示

## 技术挑战与解决方案

1. **滚动抖动问题**: 使用`requestAnimationFrame`节流，避免频繁重渲染
2. **内存泄漏**: 严格管理事件监听器和定时器清理
3. **大数量渲染**: 通过虚拟化技术限制同时渲染的元素数量
4. **列宽自适应**: 实现智能列宽分配算法，考虑内容长度和用户偏好
5. **可访问性**: 确保键盘导航和屏幕阅读器支持

该设计方案完全满足10,000行数据的高效渲染需求，同时严格遵守所有Header约束，提供流畅的滚动体验和完整的排序过滤功能。