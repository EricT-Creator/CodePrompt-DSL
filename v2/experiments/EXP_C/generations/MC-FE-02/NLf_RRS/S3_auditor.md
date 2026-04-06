# EXP-C Phase 3 — DeepSeek-V3.2 S3 Auditor (NLf × RRS)
## Task: MC-FE-02

## Constraint Review
- C1 (TS + React): PASS — import React, { useRef, useEffect, useCallback, useMemo, useState } from 'react'
- C2 (Manual virtual scroll, no windowing libs): PASS — 手动实现虚拟滚动，使用绝对定位和计算可见范围，无react-window等库
- C3 (CSS Modules, no Tailwind/inline): FAIL — 使用内联样式字符串而不是CSS Modules
- C4 (No external deps): PASS — 仅使用React和TypeScript，无外部npm包
- C5 (Single file, export default): PASS — 单一.tsx文件并以export default VirtualDataGrid导出
- C6 (Inline mock data): PASS — 在文件内使用generateMockData函数生成模拟数据，无外部文件导入

## Functionality Assessment (0-5)
Score: 4 — 实现了一个功能完整的虚拟滚动数据表格，包含排序、过滤、分页和高效的虚拟滚动。能够处理10,000行数据且性能良好。主要功能都正常工作，但CSS实现不符合CSS Modules规范。

## Corrected Code
由于C3约束失败（未使用CSS Modules），以下是修复后的完整.tsx文件：

```tsx
import React, { useRef, useEffect, useCallback, useMemo, useState } from 'react';
import styles from './VirtualDataGrid.module.css';

// ── Interfaces ──────────────────────────────────────────────────────────────

interface RowData {
  id: number;
  name: string;
  email: string;
  age: number;
  department: string;
  salary: number;
}

interface SortConfig {
  key: keyof RowData;
  direction: 'asc' | 'desc';
}

// ── Constants ───────────────────────────────────────────────────────────────

const ROW_HEIGHT = 36;
const OVERSCAN = 5;
const VIEWPORT_HEIGHT = 600;
const TOTAL_ROWS = 10000;

const DEPARTMENTS = ['Engineering', 'Marketing', 'Sales', 'HR', 'Finance', 'Design', 'Operations', 'Legal', 'Support', 'Research'];
const FIRST_NAMES = ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda', 'David', 'Elizabeth', 'William', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica', 'Thomas', 'Sarah', 'Charles', 'Karen'];
const LAST_NAMES = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin'];

// ── Mock Data Generation ────────────────────────────────────────────────────

function generateMockData(): RowData[] {
  const data: RowData[] = [];
  for (let i = 0; i < TOTAL_ROWS; i++) {
    const firstName = FIRST_NAMES[i % FIRST_NAMES.length];
    const lastName = LAST_NAMES[Math.floor(i / FIRST_NAMES.length) % LAST_NAMES.length];
    data.push({
      id: i + 1,
      name: `${firstName} ${lastName}`,
      email: `${firstName.toLowerCase()}.${lastName.toLowerCase()}${i}@example.com`,
      age: 22 + (i * 7 + 3) % 43,
      department: DEPARTMENTS[i % DEPARTMENTS.length],
      salary: 40000 + ((i * 137 + 42) % 80000),
    });
  }
  return data;
}

const ALL_DATA = generateMockData();

// ── Column definitions ──────────────────────────────────────────────────────

interface ColumnDef {
  key: keyof RowData;
  label: string;
  className?: string;
}

const COLUMNS: ColumnDef[] = [
  { key: 'id', label: 'ID', className: styles.cellId },
  { key: 'name', label: 'Name' },
  { key: 'email', label: 'Email' },
  { key: 'age', label: 'Age' },
  { key: 'department', label: 'Dept' },
  { key: 'salary', label: 'Salary', className: styles.cellSalary },
];

// ── Sub-components ──────────────────────────────────────────────────────────

const GridToolbar: React.FC<{ filterText: string; onChange: (v: string) => void; count: number }> = ({ filterText, onChange, count }) => (
  <div className={styles.toolbar}>
    <input
      className={styles.searchInput}
      placeholder="Search by name, email, department..."
      value={filterText}
      onChange={e => onChange(e.target.value)}
    />
    <span className={styles.info}>{count.toLocaleString()} rows</span>
  </div>
);

const SortableColumnHeader: React.FC<{
  col: ColumnDef;
  sortConfig: SortConfig | null;
  onSort: (key: keyof RowData) => void;
}> = ({ col, sortConfig, onSort }) => {
  const isActive = sortConfig?.key === col.key;
  let icon = '⇅';
  if (isActive) icon = sortConfig!.direction === 'asc' ? '↑' : '↓';
  return (
    <div className={styles.headerCell} onClick={() => onSort(col.key)}>
      {col.label}
      <span className={`${styles.sortIcon} ${isActive ? styles.sortIconActive : ''}`}>{icon}</span>
    </div>
  );
};

const GridRow: React.FC<{ row: RowData; index: number; top: number }> = ({ row, index, top }) => (
  <div
    className={`${styles.row} ${index % 2 === 0 ? styles.rowEven : styles.rowOdd}`}
    style={{ top, height: ROW_HEIGHT }}
  >
    <div className={`${styles.cell} ${styles.cellId}`}>{row.id}</div>
    <div className={styles.cell}>{row.name}</div>
    <div className={styles.cell}>{row.email}</div>
    <div className={styles.cell}>{row.age}</div>
    <div className={styles.cell}>{row.department}</div>
    <div className={`${styles.cell} ${styles.cellSalary}`}>${row.salary.toLocaleString()}</div>
  </div>
);

// ── Main component ──────────────────────────────────────────────────────────

const VirtualDataGrid: React.FC = () => {
  const [filterText, setFilterText] = useState('');
  const [sortConfig, setSortConfig] = useState<SortConfig | null>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [debouncedFilter, setDebouncedFilter] = useState('');

  // Debounce filter
  const handleFilterChange = useCallback((value: string) => {
    setFilterText(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedFilter(value);
    }, 200);
  }, []);

  // Filter
  const filteredData = useMemo(() => {
    if (!debouncedFilter) return ALL_DATA;
    const lower = debouncedFilter.toLowerCase();
    return ALL_DATA.filter(row =>
      row.name.toLowerCase().includes(lower) ||
      row.email.toLowerCase().includes(lower) ||
      row.department.toLowerCase().includes(lower)
    );
  }, [debouncedFilter]);

  // Sort
  const sortedData = useMemo(() => {
    if (!sortConfig) return filteredData;
    const { key, direction } = sortConfig;
    return [...filteredData].sort((a, b) => {
      const aVal = a[key];
      const bVal = b[key];
      let cmp = 0;
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        cmp = aVal.localeCompare(bVal);
      } else {
        cmp = (aVal as number) - (bVal as number);
      }
      return direction === 'asc' ? cmp : -cmp;
    });
  }, [filteredData, sortConfig]);

  // Virtual scroll range
  const totalRows = sortedData.length;
  const totalHeight = totalRows * ROW_HEIGHT;
  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const endIndex = Math.min(totalRows, Math.ceil((scrollTop + VIEWPORT_HEIGHT) / ROW_HEIGHT) + OVERSCAN);
  const visibleRows = sortedData.slice(startIndex, endIndex);

  const handleScroll = useCallback(() => {
    if (scrollRef.current) {
      setScrollTop(scrollRef.current.scrollTop);
    }
  }, []);

  const handleSort = useCallback((key: keyof RowData) => {
    setSortConfig(prev => {
      if (prev?.key === key) {
        if (prev.direction === 'asc') return { key, direction: 'desc' };
        return null;
      }
      return { key, direction: 'asc' };
    });
  }, []);

  return (
    <div className={styles.container}>
      <GridToolbar filterText={filterText} onChange={handleFilterChange} count={totalRows} />
      <div className={styles.headerRow}>
        {COLUMNS.map(col => (
          <SortableColumnHeader key={col.key} col={col} sortConfig={sortConfig} onSort={handleSort} />
        ))}
      </div>
      <div className={styles.scrollContainer} ref={scrollRef} onScroll={handleScroll}>
        <div className={styles.spacer} style={{ height: totalHeight }}>
          {visibleRows.map((row, i) => (
            <GridRow
              key={row.id}
              row={row}
              index={startIndex + i}
              top={(startIndex + i) * ROW_HEIGHT}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default VirtualDataGrid;
```

**注意**: 修复后的代码假设存在 `VirtualDataGrid.module.css` 文件，其中包含所有CSS样式。原始的内联CSS字符串需要提取到该CSS Modules文件中。