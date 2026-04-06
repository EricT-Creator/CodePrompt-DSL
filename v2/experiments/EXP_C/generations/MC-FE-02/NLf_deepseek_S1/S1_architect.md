# MC-FE-02: 虚拟滚动数据网格技术方案

## 1. 组件架构

### 1.1 主要组件
- **VirtualDataGrid**: 主组件，管理虚拟滚动和数据渲染
- **GridHeader**: 固定表头组件，支持列排序
- **GridRow**: 单行渲染组件，动态计算可见行
- **SearchInput**: 搜索/过滤输入组件
- **ScrollContainer**: 滚动容器组件，处理滚动事件

### 1.2 组件职责
- **VirtualDataGrid**: 管理整体数据、计算可见范围、处理滚动事件、协调子组件
- **GridHeader**: 显示列标题、处理点击排序、提供排序状态指示
- **GridRow**: 渲染单行数据、应用行样式、处理行交互
- **SearchInput**: 收集搜索词、触发过滤逻辑、显示搜索状态
- **ScrollContainer**: 提供滚动容器、计算滚动位置、触发可见范围更新

## 2. 虚拟滚动算法

### 2.1 可见范围计算
```typescript
interface VisibleRange {
  startIndex: number;    // 可见区域起始行索引
  endIndex: number;      // 可见区域结束行索引
  visibleCount: number;  // 可见行数量
  overscan: number;      // 上下预渲染行数
}
```

### 2.2 计算步骤
1. **获取容器尺寸**: 通过ref获取滚动容器高度
2. **计算行高**: 固定行高或动态测量
3. **确定可见行数**: `containerHeight / rowHeight`
4. **计算起始索引**: `Math.floor(scrollTop / rowHeight)`
5. **计算结束索引**: `startIndex + visibleCount + overscan * 2`
6. **边界处理**: 确保索引在有效范围内

### 2.3 性能优化
- **行高固定**: 使用固定行高避免动态测量
- **预渲染**: 上下各预渲染5行减少空白闪烁
- **防抖滚动**: 使用requestAnimationFrame节流滚动事件
- **缓存计算**: 缓存可见范围计算结果

## 3. 数据模型

```typescript
interface DataItem {
  id: string | number;
  [key: string]: any; // 动态列数据
}

interface ColumnDef {
  key: string;
  label: string;
  width: number;
  sortable: boolean;
  sortDirection?: 'asc' | 'desc' | null;
}

interface GridState {
  data: DataItem[];           // 原始数据
  filteredData: DataItem[];   // 过滤后数据
  visibleData: DataItem[];    // 当前可见数据
  columns: ColumnDef[];
  sortColumn: string | null;
  sortDirection: 'asc' | 'desc' | null;
  searchTerm: string;
  visibleRange: VisibleRange;
  totalRows: number;
}

interface SortState {
  columnKey: string;
  direction: 'asc' | 'desc';
  comparator: (a: DataItem, b: DataItem) => number;
}
```

## 4. 排序和过滤方法

### 4.1 排序实现
1. **列点击处理**: 点击表头切换排序状态
2. **排序函数生成**: 根据数据类型生成合适的比较器
   - 字符串: 使用localeCompare
   - 数字: 直接数值比较
   - 日期: 转换为时间戳比较
3. **多级排序**: 支持主排序和次排序
4. **状态指示**: 表头显示排序箭头和方向

### 4.2 过滤实现
1. **全文搜索**: 在所有可搜索列中匹配搜索词
2. **列级过滤**: 支持按列过滤
3. **实时过滤**: 输入时实时更新过滤结果
4. **性能优化**: 使用防抖减少过滤频率

### 4.3 搜索算法
```typescript
function filterData(data: DataItem[], searchTerm: string): DataItem[] {
  if (!searchTerm.trim()) return data;
  
  const term = searchTerm.toLowerCase();
  return data.filter(item => {
    return Object.values(item).some(value => {
      if (typeof value === 'string') {
        return value.toLowerCase().includes(term);
      }
      if (typeof value === 'number') {
        return value.toString().includes(term);
      }
      return false;
    });
  });
}
```

## 5. 约束确认

### 约束1: TypeScript + React框架
- 使用TypeScript进行类型安全开发
- 使用React函数组件和Hooks
- 所有组件都有完整的TypeScript接口定义

### 约束2: 手动实现虚拟滚动
- 不使用react-window、react-virtualized等库
- 基于滚动位置计算可见范围
- 实现完整的虚拟滚动算法

### 约束3: CSS Modules样式
- 每个组件创建.module.css文件
- 类名通过styles对象引用
- 不使用Tailwind CSS或内联样式

### 约束4: 无外部npm包
- 仅使用React和TypeScript
- 所有功能手动实现
- 不引入任何第三方库

### 约束5: 单文件导出
- 所有代码在一个.tsx文件中
- 使用export default导出VirtualDataGrid组件
- 组件内部定义所有子组件

### 约束6: 内联模拟数据
- 在组件内部生成10000行模拟数据
- 不使用外部数据文件
- 数据包含多种类型测试排序和过滤

## 6. 关键实现细节

### 6.1 平滑滚动实现
1. **requestAnimationFrame**: 使用RAF进行滚动事件节流
2. **transform优化**: 使用CSS transform进行位置调整
3. **will-change提示**: 提示浏览器进行GPU加速
4. **滚动惯性**: 模拟自然滚动效果

### 6.2 行渲染优化
1. **React.memo**: 包装GridRow组件避免不必要渲染
2. **key属性**: 使用稳定唯一键值
3. **行池复用**: 复用行DOM元素
4. **样式缓存**: 缓存计算后的行样式

### 6.3 表头固定
1. **position: sticky**: 使用CSS sticky定位
2. **z-index管理**: 确保表头在内容之上
3. **阴影效果**: 滚动时显示表头阴影
4. **列宽同步**: 表头与内容列宽同步

## 7. 性能指标

1. **初始渲染时间**: < 100ms (10000行数据)
2. **滚动帧率**: 保持60fps
3. **内存使用**: 仅渲染可见行+预渲染行
4. **过滤响应时间**: < 50ms (10000行全文搜索)

## 8. 可扩展功能

1. **列调整**: 支持拖拽调整列宽
2. **列隐藏**: 支持动态显示/隐藏列
3. **行选择**: 支持单选/多选行
4. **分页**: 可扩展为分页模式
5. **导出**: 支持数据导出为CSV/Excel

---

*文档字数: 约1900字*