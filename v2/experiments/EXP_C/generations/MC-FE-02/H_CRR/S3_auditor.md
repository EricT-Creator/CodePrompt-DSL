## Constraint Review
- C1 [L]TS [F]React: PASS — File uses TypeScript throughout (`DataRow`, `ColumnDef`, `VirtualMetrics` interfaces, typed state hooks) and React functional component pattern.
- C2 [!D]NO_VIRT_LIB [SCROLL]MANUAL: PASS — Virtual scrolling is manually implemented via `scrollTop` tracking, `requestAnimationFrame` throttling, computing `startIndex`/`endIndex` with overscan, and absolute positioning of rows. No external virtualization library imported.
- C3 [Y]CSS_MODULES [!Y]NO_TW_INLINE: FAIL — Code uses inline style objects (`const css: Record<string, React.CSSProperties>`) instead of importing a `.module.css` file. No Tailwind is used (that part passes), but the CSS Modules requirement is violated.
- C4 [D]NO_EXTERNAL: PASS — Only `react` is imported; no external dependencies used.
- C5 [O]SFC [EXP]DEFAULT: PASS — `DataGrid` is a single functional component exported as `export default DataGrid`.
- C6 [DT]INLINE_MOCK: PASS — Mock data is generated inline via `generateMockData()` with hardcoded arrays (`DEPARTMENTS`, `FIRST_NAMES`, `LAST_NAMES`); no external data source.

## Functionality Assessment (0-5)
Score: 5 — Fully functional virtual-scroll data grid rendering 10,000 rows efficiently. Implements column sorting (toggling asc/desc), full-text filtering across all columns, rAF-throttled scroll handling, overscan for smooth scrolling, row striping, and real-time display of scroll position and visible row range.

## Corrected Code
```tsx
import React, { useState, useRef, useMemo, useCallback, useEffect } from 'react';
import css from './DataGrid.module.css';

// ─── Types ───────────────────────────────────────────────────────────────────

interface DataRow {
  id: string | number;
  [key: string]: unknown;
}

interface ColumnDef {
  key: string;
  header: string;
  width: number;
  sortable: boolean;
}

interface VirtualMetrics {
  startIndex: number;
  endIndex: number;
  visibleCount: number;
  totalHeight: number;
  offsetY: number;
}

// ─── Constants ───────────────────────────────────────────────────────────────

const ROW_HEIGHT = 40;
const OVERSCAN = 5;
const CONTAINER_HEIGHT = 400;
const TOTAL_ROWS = 10000;

// ─── Mock data ───────────────────────────────────────────────────────────────

const COLUMNS: ColumnDef[] = [
  { key: 'id', header: 'ID', width: 80, sortable: true },
  { key: 'name', header: 'Name', width: 200, sortable: true },
  { key: 'email', header: 'Email', width: 250, sortable: true },
  { key: 'department', header: 'Department', width: 150, sortable: true },
  { key: 'salary', header: 'Salary', width: 120, sortable: true },
];

const DEPARTMENTS = ['Engineering', 'Marketing', 'Sales', 'HR', 'Finance', 'Operations', 'Legal', 'Support'];
const FIRST_NAMES = ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank', 'Grace', 'Hector', 'Ivy', 'Jack'];
const LAST_NAMES = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez'];

function generateMockData(count: number): DataRow[] {
  const rows: DataRow[] = [];
  for (let i = 0; i < count; i++) {
    const first = FIRST_NAMES[i % FIRST_NAMES.length];
    const last = LAST_NAMES[Math.floor(i / FIRST_NAMES.length) % LAST_NAMES.length];
    rows.push({
      id: i + 1,
      name: `${first} ${last}`,
      email: `${first.toLowerCase()}.${last.toLowerCase()}@example.com`,
      department: DEPARTMENTS[i % DEPARTMENTS.length],
      salary: 40000 + Math.floor(Math.random() * 80000),
    });
  }
  return rows;
}

const ALL_ROWS = generateMockData(TOTAL_ROWS);

// ─── Main Component ─────────────────────────────────────────────────────────

const DataGrid: React.FC = () => {
  const [filterText, setFilterText] = useState('');
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [scrollTop, setScrollTop] = useState(0);
  const viewportRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number>(0);

  // Filter
  const filteredRows = useMemo(() => {
    if (!filterText) return ALL_ROWS;
    const lower = filterText.toLowerCase();
    return ALL_ROWS.filter((row) =>
      Object.values(row).some((val) => String(val).toLowerCase().includes(lower)),
    );
  }, [filterText]);

  // Sort
  const sortedRows = useMemo(() => {
    if (!sortColumn) return filteredRows;
    const sorted = [...filteredRows].sort((a, b) => {
      const valA = a[sortColumn];
      const valB = b[sortColumn];
      let comparison = 0;
      if (typeof valA === 'number' && typeof valB === 'number') {
        comparison = valA - valB;
      } else {
        comparison = String(valA).localeCompare(String(valB));
      }
      return sortDirection === 'asc' ? comparison : -comparison;
    });
    return sorted;
  }, [filteredRows, sortColumn, sortDirection]);

  // Virtual scroll metrics
  const metrics: VirtualMetrics = useMemo(() => {
    const visibleCount = Math.ceil(CONTAINER_HEIGHT / ROW_HEIGHT);
    const totalHeight = sortedRows.length * ROW_HEIGHT;
    let start = Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN;
    if (start < 0) start = 0;
    let end = start + visibleCount + OVERSCAN * 2;
    if (end > sortedRows.length) end = sortedRows.length;
    return {
      startIndex: start,
      endIndex: end,
      visibleCount,
      totalHeight,
      offsetY: start * ROW_HEIGHT,
    };
  }, [scrollTop, sortedRows.length]);

  // Visible rows
  const visibleRows = useMemo(
    () => sortedRows.slice(metrics.startIndex, metrics.endIndex),
    [sortedRows, metrics.startIndex, metrics.endIndex],
  );

  // Scroll handler (throttled via rAF)
  const handleScroll = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => {
      if (viewportRef.current) {
        setScrollTop(viewportRef.current.scrollTop);
      }
    });
  }, []);

  useEffect(() => {
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  // Sort toggle
  const handleSort = useCallback(
    (key: string) => {
      if (sortColumn === key) {
        setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
      } else {
        setSortColumn(key);
        setSortDirection('asc');
      }
    },
    [sortColumn],
  );

  const sortIndicator = (key: string): string => {
    if (sortColumn !== key) return '';
    return sortDirection === 'asc' ? ' ▲' : ' ▼';
  };

  return (
    <div className={css.wrapper}>
      <div className={css.title}>Virtual Scroll Data Grid</div>
      <div className={css.subtitle}>
        {sortedRows.length.toLocaleString()} rows · Rendering {visibleRows.length} visible
      </div>

      {/* Controls */}
      <div className={css.controls}>
        <input
          className={css.searchInput}
          placeholder="Search all columns..."
          value={filterText}
          onChange={(e) => {
            setFilterText(e.target.value);
            setScrollTop(0);
            if (viewportRef.current) viewportRef.current.scrollTop = 0;
          }}
        />
        {COLUMNS.filter((c) => c.sortable).map((col) => (
          <button
            key={col.key}
            className={`${css.sortBtn} ${sortColumn === col.key ? css.sortBtnActive : ''}`}
            onClick={() => handleSort(col.key)}
          >
            {col.header}{sortIndicator(col.key)}
          </button>
        ))}
      </div>

      {/* Grid */}
      <div className={css.grid}>
        {/* Header */}
        <div className={css.headerRow}>
          {COLUMNS.map((col) => (
            <div
              key={col.key}
              className={css.headerCell}
              style={{ width: col.width, flexShrink: 0 }}
              onClick={() => col.sortable && handleSort(col.key)}
            >
              {col.header}{sortIndicator(col.key)}
            </div>
          ))}
        </div>

        {/* Viewport */}
        <div className={css.viewport} ref={viewportRef} onScroll={handleScroll}>
          <div className={css.spacer} style={{ height: metrics.totalHeight }}>
            {visibleRows.map((row, i) => {
              const absoluteIndex = metrics.startIndex + i;
              return (
                <div
                  key={String(row.id)}
                  className={`${css.row} ${absoluteIndex % 2 === 0 ? css.rowEven : ''}`}
                  style={{
                    top: absoluteIndex * ROW_HEIGHT,
                    height: ROW_HEIGHT,
                  }}
                >
                  {COLUMNS.map((col) => (
                    <div
                      key={col.key}
                      className={css.cell}
                      style={{ width: col.width, flexShrink: 0 }}
                    >
                      {col.key === 'salary'
                        ? `$${Number(row[col.key]).toLocaleString()}`
                        : String(row[col.key] ?? '')}
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className={css.info}>
        Scroll position: {Math.round(scrollTop)}px · Rows {metrics.startIndex + 1}–{metrics.endIndex} of{' '}
        {sortedRows.length.toLocaleString()}
      </div>
    </div>
  );
};

export default DataGrid;
```
