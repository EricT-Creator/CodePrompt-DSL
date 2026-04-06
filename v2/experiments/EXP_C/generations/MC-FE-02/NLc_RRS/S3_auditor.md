# MC-FE-02 代码审查报告

## Constraint Review
- C1 (TS + React): PASS — 使用TypeScript定义接口（RowData、SortConfig）和React组件
- C2 (Manual virtual scroll, no windowing libs): PASS — 手动实现虚拟滚动（计算startIndex/endIndex、绝对定位渲染）
- C3 (CSS Modules, no Tailwind/inline): FAIL — 使用inline style对象（css常量），不是真正的CSS Modules文件
- C4 (No external deps): PASS — 没有import任何外部依赖库，只使用React内置hooks
- C5 (Single file, export default): PASS — 所有代码在单个文件中，最后export default DataGrid
- C6 (Inline mock data): PASS — 通过generateData函数内联生成10000行模拟数据

## Functionality Assessment (0-5)
Score: 4 — 代码实现了完整的虚拟滚动数据表格，功能包括：10,000行数据渲染、过滤搜索、多列排序、性能优化（memo、useCallback、requestAnimationFrame防抖）。代码结构清晰，虚拟滚动实现正确。扣分点：缺少真正的CSS Modules支持。

## Corrected Code
由于C3约束失败（要求CSS Modules，禁止inline styles），需要转换为真正的CSS Modules。以下是修正后的代码：

```tsx
import React, { useRef, useState, useMemo, useCallback, memo } from 'react';
import styles from './DataGrid.module.css';

// ── Types ──

interface RowData {
  id: number;
  name: string;
  email: string;
  age: number;
  city: string;
  score: number;
}

interface SortConfig {
  column: keyof RowData | null;
  direction: 'asc' | 'desc' | null;
}

// ── Constants ──

const ROW_HEIGHT = 36;
const VIEWPORT_HEIGHT = 600;
const OVERSCAN = 5;
const TOTAL_ROWS = 10000;

const CITIES = [
  'New York', 'London', 'Tokyo', 'Paris', 'Berlin',
  'Sydney', 'Toronto', 'Mumbai', 'Beijing', 'Seoul',
  'Moscow', 'Dubai', 'Singapore', 'Bangkok', 'Rome',
];

const COLUMNS: { key: keyof RowData; label: string; width: number; sortable: boolean }[] = [
  { key: 'id', label: 'ID', width: 80, sortable: false },
  { key: 'name', label: 'Name', width: 200, sortable: true },
  { key: 'email', label: 'Email', width: 280, sortable: false },
  { key: 'age', label: 'Age', width: 80, sortable: true },
  { key: 'city', label: 'City', width: 150, sortable: false },
  { key: 'score', label: 'Score', width: 100, sortable: true },
];

// ── Mock Data Generator ──

function generateData(count: number): RowData[] {
  const data: RowData[] = [];
  for (let i = 0; i < count; i++) {
    data.push({
      id: i + 1,
      name: `User ${i + 1}`,
      email: `user${i + 1}@example.com`,
      age: 18 + (i % 50),
      city: CITIES[i % CITIES.length],
      score: Math.round(((i * 7 + 13) % 100) * 10) / 10,
    });
  }
  return data;
}

// ── GridRow (memoized) ──

const GridRow = memo<{
  row: RowData;
  index: number;
  top: number;
}>(({ row, index, top }) => (
  <div
    className={`${styles.row} ${index % 2 === 0 ? styles.rowEven : ''}`}
    style={{ top }}
  >
    {COLUMNS.map((col) => (
      <div key={col.key} className={styles.cell} style={{ width: col.width, flexShrink: 0 }}>
        {String(row[col.key])}
      </div>
    ))}
  </div>
));

GridRow.displayName = 'GridRow';

// ── FilterBar ──

const FilterBar: React.FC<{
  value: string;
  onChange: (v: string) => void;
  total: number;
  filtered: number;
}> = ({ value, onChange, total, filtered }) => (
  <div className={styles.filterBar}>
    <span className={styles.filterLabel}>Filter:</span>
    <input
      className={styles.filterInput}
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder="Search by name or email..."
    />
    <span className={styles.stats}>
      {filtered === total
        ? `${total.toLocaleString()} rows`
        : `${filtered.toLocaleString()} / ${total.toLocaleString()} rows`}
    </span>
  </div>
);

// ── GridHeader ──

const GridHeader: React.FC<{
  sort: SortConfig;
  onSort: (column: keyof RowData) => void;
}> = ({ sort, onSort }) => {
  const getSortIndicator = (col: keyof RowData): string => {
    if (sort.column !== col) return '';
    return sort.direction === 'asc' ? ' ▲' : ' ▼';
  };

  return (
    <div className={styles.headerRow}>
      {COLUMNS.map((col) => (
        <div
          key={col.key}
          className={`${styles.headerCell} ${col.sortable ? styles.headerCellSortable : ''}`}
          style={{ width: col.width, flexShrink: 0 }}
          onClick={() => col.sortable && onSort(col.key)}
        >
          {col.label}
          {col.sortable && (
            <span className={styles.sortArrow}>{getSortIndicator(col.key)}</span>
          )}
        </div>
      ))}
    </div>
  );
};

// ── DataGrid (root) ──

const DataGrid: React.FC = () => {
  const rawDataRef = useRef<RowData[]>(generateData(TOTAL_ROWS));
  const scrollRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [filter, setFilter] = useState('');
  const [sort, setSort] = useState<SortConfig>({ column: null, direction: null });
  const rafRef = useRef<number | null>(null);

  const filteredData = useMemo(() => {
    if (!filter.trim()) return rawDataRef.current;
    const lower = filter.toLowerCase();
    return rawDataRef.current.filter(
      (row) =>
        row.name.toLowerCase().includes(lower) ||
        row.email.toLowerCase().includes(lower)
    );
  }, [filter]);

  const sortedData = useMemo(() => {
    if (!sort.column || !sort.direction) return filteredData;
    const col = sort.column;
    const dir = sort.direction === 'asc' ? 1 : -1;
    return [...filteredData].sort((a, b) => {
      const va = a[col];
      const vb = b[col];
      if (typeof va === 'string' && typeof vb === 'string') {
        return va.localeCompare(vb) * dir;
      }
      return ((va as number) - (vb as number)) * dir;
    });
  }, [filteredData, sort]);

  const totalRows = sortedData.length;
  const totalHeight = totalRows * ROW_HEIGHT;

  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const endIndex = Math.min(
    totalRows - 1,
    Math.ceil((scrollTop + VIEWPORT_HEIGHT) / ROW_HEIGHT) + OVERSCAN
  );

  const visibleRows = sortedData.slice(startIndex, endIndex + 1);

  const handleScroll = useCallback(() => {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => {
      if (scrollRef.current) {
        setScrollTop(scrollRef.current.scrollTop);
      }
    });
  }, []);

  const handleSort = useCallback(
    (column: keyof RowData) => {
      setSort((prev) => {
        if (prev.column !== column) return { column, direction: 'asc' };
        if (prev.direction === 'asc') return { column, direction: 'desc' };
        return { column: null, direction: null };
      });
    },
    []
  );

  return (
    <div className={styles.container}>
      <div className={styles.title}>Virtual Scroll Data Grid</div>
      <FilterBar
        value={filter}
        onChange={setFilter}
        total={TOTAL_ROWS}
        filtered={totalRows}
      />
      <GridHeader sort={sort} onSort={handleSort} />
      <div
        ref={scrollRef}
        className={styles.viewport}
        onScroll={handleScroll}
      >
        <div style={{ height: totalHeight, position: 'relative', willChange: 'transform' }}>
          {visibleRows.map((row, i) => {
            const actualIndex = startIndex + i;
            return (
              <GridRow
                key={row.id}
                row={row}
                index={actualIndex}
                top={actualIndex * ROW_HEIGHT}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default DataGrid;
```

注意：需要创建对应的CSS Modules文件 `DataGrid.module.css`。
```css
.container {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  max-width: 960px;
  margin: 0 auto;
  padding: 20px;
  background: #f8f9fa;
  min-height: 100vh;
}

.title {
  text-align: center;
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 16px;
  color: #2d3436;
}

.filterBar {
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.filterInput {
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid #ddd;
  font-size: 14px;
  width: 300px;
  outline: none;
}

.filterLabel {
  font-size: 14px;
  color: #636e72;
}

.stats {
  font-size: 12px;
  color: #b2bec3;
  margin-left: auto;
}

.headerRow {
  display: flex;
  background: #2d3436;
  color: #fff;
  font-weight: 600;
  font-size: 13px;
  border-radius: 6px 6px 0 0;
}

.headerCell {
  padding: 10px 12px;
  border-right: 1px solid #636e72;
  cursor: default;
  user-select: none;
  display: flex;
  align-items: center;
  gap: 4px;
}

.headerCellSortable {
  cursor: pointer;
}

.viewport {
  height: 600px;
  overflow-y: auto;
  border: 1px solid #ddd;
  border-top: none;
  border-radius: 0 0 6px 6px;
  background: #fff;
  position: relative;
}

.row {
  display: flex;
  position: absolute;
  width: 100%;
  border-bottom: 1px solid #f0f0f0;
  font-size: 13px;
  transition: background 0.1s;
}

.rowEven {
  background: #fafafa;
}

.cell {
  padding: 8px 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sortArrow {
  font-size: 10px;
  margin-left: 2px;
}
```