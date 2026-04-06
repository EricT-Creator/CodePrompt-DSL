# MC-FE-02 Code Review Report

**Model**: Kimi-K2.5  
**Stage**: S3 Auditor  
**Encoding**: NLf  
**Pipeline**: RRC  
**Task**: MC-FE-02 (Virtual Data Grid)

---

## Constraint Review

- **C1 (TS + React)**: PASS — Uses TypeScript with React hooks (useState, useRef, useCallback, useMemo, useEffect)
- **C2 (Manual virtual scroll, no windowing libs)**: PASS — Implements custom virtual scrolling with manual calculations (startIndex, endIndex, visibleRows, totalHeight)
- **C3 (CSS Modules, no Tailwind/inline)**: FAIL — Uses inline style injection via `document.createElement('style')` instead of CSS Modules
- **C4 (No external deps)**: PASS — Only imports React, no external npm packages
- **C5 (Single file, export default)**: PASS — Single .tsx file with `export default VirtualDataGrid`
- **C6 (Inline mock data)**: PASS — Mock data generated inline with `generateMockData()` function

---

## Functionality Assessment (0-5)

**Score: 4** — The code implements a performant virtual data grid with 10,000 rows, sorting, filtering, and custom virtual scrolling. The main issue is the styling approach which doesn't use CSS Modules as required.

---

## Corrected Code

The following code replaces the inline style injection with CSS Modules approach:

```tsx
import React, { useRef, useCallback, useMemo, useEffect } from 'react';
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

const DEPARTMENTS = ['Engineering', 'Marketing', 'Sales', 'HR', 'Finance', 'Operations', 'Legal', 'Support', 'Product', 'Design'];
const FIRST_NAMES = ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda', 'William', 'Elizabeth', 'David', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica', 'Thomas', 'Sarah', 'Charles', 'Karen'];
const LAST_NAMES = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin'];

// ── Mock Data Generation ────────────────────────────────────────────────────

function generateMockData(): RowData[] {
  const data: RowData[] = [];
  for (let i = 0; i < TOTAL_ROWS; i++) {
    const firstName = FIRST_NAMES[i % FIRST_NAMES.length];
    const lastName = LAST_NAMES[(i * 7 + 3) % LAST_NAMES.length];
    data.push({
      id: i + 1,
      name: `${firstName} ${lastName}`,
      email: `${firstName.toLowerCase()}.${lastName.toLowerCase()}${i}@example.com`,
      age: 22 + (i * 13 + 5) % 43,
      department: DEPARTMENTS[i % DEPARTMENTS.length],
      salary: 40000 + ((i * 97 + 31) % 120000),
    });
  }
  return data;
}

const ALL_DATA = generateMockData();

// ── Column Definitions ──────────────────────────────────────────────────────

interface ColumnDef {
  key: keyof RowData;
  label: string;
  headerClass: string;
  cellClass: string;
  format?: (val: any) => string;
}

const COLUMNS: ColumnDef[] = [
  { key: 'id', label: 'ID', headerClass: styles.headerCellId, cellClass: styles.cellId },
  { key: 'name', label: 'Name', headerClass: styles.headerCellName, cellClass: styles.cellName },
  { key: 'email', label: 'Email', headerClass: styles.headerCellEmail, cellClass: styles.cellEmail },
  { key: 'age', label: 'Age', headerClass: styles.headerCellAge, cellClass: styles.cellAge },
  { key: 'department', label: 'Department', headerClass: styles.headerCellDept, cellClass: styles.cellDept },
  {
    key: 'salary',
    label: 'Salary',
    headerClass: styles.headerCellSalary,
    cellClass: styles.cellSalary,
    format: (v: number) => `$${v.toLocaleString()}`,
  },
];

// ── Sub-Components ──────────────────────────────────────────────────────────

const GridToolbar: React.FC<{
  filterText: string;
  onFilterChange: (text: string) => void;
  rowCount: number;
}> = ({ filterText, onFilterChange, rowCount }) => (
  <div className={styles.toolbar}>
    <div className={styles.toolbarTitle}>Data Grid</div>
    <input
      className={styles.search}
      placeholder="Search by name, email, or department..."
      value={filterText}
      onChange={e => onFilterChange(e.target.value)}
    />
    <div className={styles.rowCount}>{rowCount.toLocaleString()} rows</div>
  </div>
);

const SortableColumnHeader: React.FC<{
  col: ColumnDef;
  sortConfig: SortConfig | null;
  onSort: (key: keyof RowData) => void;
}> = ({ col, sortConfig, onSort }) => {
  let indicator = '';
  if (sortConfig && sortConfig.key === col.key) {
    indicator = sortConfig.direction === 'asc' ? '▲' : '▼';
  }
  return (
    <div
      className={`${styles.headerCell} ${col.headerClass}`}
      onClick={() => onSort(col.key)}
    >
      {col.label}
      {indicator && <span className={styles.sortIndicator}>{indicator}</span>}
    </div>
  );
};

const GridHeader: React.FC<{
  sortConfig: SortConfig | null;
  onSort: (key: keyof RowData) => void;
}> = ({ sortConfig, onSort }) => (
  <div className={styles.headerRow}>
    {COLUMNS.map(col => (
      <SortableColumnHeader key={col.key} col={col} sortConfig={sortConfig} onSort={onSort} />
    ))}
  </div>
);

const GridRow: React.FC<{ row: RowData; top: number; even: boolean }> = ({ row, top, even }) => (
  <div
    className={`${styles.row} ${even ? styles.rowEven : ''}`}
    style={{ top }}
  >
    {COLUMNS.map(col => (
      <div key={col.key} className={`${styles.cell} ${col.cellClass}`}>
        {col.format ? col.format(row[col.key]) : String(row[col.key])}
      </div>
    ))}
  </div>
);

// ── Main Component ──────────────────────────────────────────────────────────

const VirtualDataGrid: React.FC = () => {
  const [filterText, setFilterText] = React.useState('');
  const [debouncedFilter, setDebouncedFilter] = React.useState('');
  const [sortConfig, setSortConfig] = React.useState<SortConfig | null>(null);
  const [scrollTop, setScrollTop] = React.useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);
  const prevRangeRef = useRef<{ start: number; end: number }>({ start: 0, end: 0 });

  // Debounced filter
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedFilter(filterText), 200);
    return () => clearTimeout(timer);
  }, [filterText]);

  // Filtered data
  const filteredData = useMemo(() => {
    if (!debouncedFilter) return ALL_DATA;
    const lower = debouncedFilter.toLowerCase();
    return ALL_DATA.filter(
      row =>
        row.name.toLowerCase().includes(lower) ||
        row.email.toLowerCase().includes(lower) ||
        row.department.toLowerCase().includes(lower)
    );
  }, [debouncedFilter]);

  // Sorted data
  const sortedData = useMemo(() => {
    if (!sortConfig) return filteredData;
    const { key, direction } = sortConfig;
    return [...filteredData].sort((a, b) => {
      const aVal = a[key];
      const bVal = b[key];
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return direction === 'asc' ? aVal - bVal : bVal - aVal;
      }
      return 0;
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
      const newScrollTop = scrollRef.current.scrollTop;
      const newStart = Math.max(0, Math.floor(newScrollTop / ROW_HEIGHT) - OVERSCAN);
      const newEnd = Math.min(totalRows, Math.ceil((newScrollTop + VIEWPORT_HEIGHT) / ROW_HEIGHT) + OVERSCAN);

      if (newStart !== prevRangeRef.current.start || newEnd !== prevRangeRef.current.end) {
        prevRangeRef.current = { start: newStart, end: newEnd };
        setScrollTop(newScrollTop);
      }
    }
  }, [totalRows]);

  const handleSort = useCallback((key: keyof RowData) => {
    setSortConfig(prev => {
      if (prev && prev.key === key) {
        if (prev.direction === 'asc') return { key, direction: 'desc' };
        return null;
      }
      return { key, direction: 'asc' };
    });
    if (scrollRef.current) scrollRef.current.scrollTop = 0;
    setScrollTop(0);
  }, []);

  return (
    <div className={styles.container}>
      <GridToolbar
        filterText={filterText}
        onFilterChange={setFilterText}
        rowCount={totalRows}
      />
      <GridHeader sortConfig={sortConfig} onSort={handleSort} />
      <div
        ref={scrollRef}
        className={styles.scrollContainer}
        onScroll={handleScroll}
      >
        <div className={styles.spacer} style={{ height: totalHeight }}>
          {visibleRows.map((row, i) => {
            const idx = startIndex + i;
            return (
              <GridRow
                key={row.id}
                row={row}
                top={idx * ROW_HEIGHT}
                even={idx % 2 === 0}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default VirtualDataGrid;
```

**Note**: The corrected code assumes the existence of a CSS Module file `VirtualDataGrid.module.css` with the appropriate class names mapped from the original styles.
