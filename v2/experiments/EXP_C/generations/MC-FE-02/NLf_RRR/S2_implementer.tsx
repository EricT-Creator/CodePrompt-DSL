import React, { useRef, useCallback, useMemo, useEffect } from 'react';

// ─── Interfaces ──────────────────────────────────────────────

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

// ─── Style Injection ─────────────────────────────────────────

const STYLE_ID = 'vdg-styles';
const CSS = `
.vdg-root {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
  background: #f9fafb;
  min-height: 100vh;
}
.vdg-toolbar {
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.vdg-toolbar input {
  padding: 8px 14px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  width: 300px;
  outline: none;
}
.vdg-toolbar input:focus {
  border-color: #6366f1;
}
.vdg-info {
  font-size: 13px;
  color: #6b7280;
}
.vdg-container {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}
.vdg-header-row {
  display: grid;
  grid-template-columns: 60px 1fr 1.4fr 60px 1fr 100px;
  background: #f3f4f6;
  border-bottom: 2px solid #e5e7eb;
  position: sticky;
  top: 0;
  z-index: 1;
}
.vdg-header-cell {
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  cursor: pointer;
  user-select: none;
  display: flex;
  align-items: center;
  gap: 4px;
  border-right: 1px solid #e5e7eb;
}
.vdg-header-cell:last-child {
  border-right: none;
}
.vdg-header-cell:hover {
  background: #e5e7eb;
}
.vdg-sort-indicator {
  font-size: 10px;
  color: #6366f1;
}
.vdg-scroll-container {
  height: 600px;
  overflow-y: auto;
  position: relative;
}
.vdg-spacer {
  position: relative;
  width: 100%;
}
.vdg-row {
  display: grid;
  grid-template-columns: 60px 1fr 1.4fr 60px 1fr 100px;
  position: absolute;
  width: 100%;
  border-bottom: 1px solid #f3f4f6;
}
.vdg-row:hover {
  background: #f9fafb;
}
.vdg-cell {
  padding: 8px 12px;
  font-size: 13px;
  color: #1f2937;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border-right: 1px solid #f3f4f6;
}
.vdg-cell:last-child {
  border-right: none;
}
.vdg-row-even {
  background: #fafbfc;
}
`;

function injectStyles() {
  if (typeof document !== 'undefined' && !document.getElementById(STYLE_ID)) {
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = CSS;
    document.head.appendChild(style);
  }
}

// ─── Mock Data Generation ────────────────────────────────────

const DEPARTMENTS = ['Engineering', 'Marketing', 'Sales', 'Design', 'HR', 'Finance', 'Operations', 'Legal'];
const FIRST_NAMES = ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank', 'Grace', 'Hank', 'Iris', 'Jack',
  'Karen', 'Leo', 'Mia', 'Noah', 'Olivia', 'Paul', 'Quinn', 'Rose', 'Sam', 'Tina'];
const LAST_NAMES = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
  'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
  'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin'];

function generateMockData(): RowData[] {
  const data: RowData[] = [];
  for (let i = 0; i < 10000; i++) {
    const firstName = FIRST_NAMES[i % FIRST_NAMES.length];
    const lastName = LAST_NAMES[Math.floor(i / FIRST_NAMES.length) % LAST_NAMES.length];
    data.push({
      id: i + 1,
      name: `${firstName} ${lastName}`,
      email: `${firstName.toLowerCase()}.${lastName.toLowerCase()}${i}@example.com`,
      age: 22 + (i % 43),
      department: DEPARTMENTS[i % DEPARTMENTS.length],
      salary: 40000 + ((i * 137) % 80000),
    });
  }
  return data;
}

const ALL_DATA: RowData[] = generateMockData();

// ─── Constants ───────────────────────────────────────────────

const ROW_HEIGHT = 36;
const OVERSCAN = 5;
const COLUMNS: { key: keyof RowData; label: string }[] = [
  { key: 'id', label: 'ID' },
  { key: 'name', label: 'Name' },
  { key: 'email', label: 'Email' },
  { key: 'age', label: 'Age' },
  { key: 'department', label: 'Dept' },
  { key: 'salary', label: 'Salary' },
];

// ─── Sub-Components ──────────────────────────────────────────

function SortableColumnHeader({
  column,
  sortConfig,
  onClick,
}: {
  column: { key: keyof RowData; label: string };
  sortConfig: SortConfig | null;
  onClick: (key: keyof RowData) => void;
}) {
  const isActive = sortConfig?.key === column.key;
  const indicator = isActive ? (sortConfig!.direction === 'asc' ? '▲' : '▼') : '';

  return (
    <div className="vdg-header-cell" onClick={() => onClick(column.key)}>
      {column.label}
      {indicator && <span className="vdg-sort-indicator">{indicator}</span>}
    </div>
  );
}

function GridRow({ row, style, isEven }: { row: RowData; style: React.CSSProperties; isEven: boolean }) {
  return (
    <div className={'vdg-row' + (isEven ? ' vdg-row-even' : '')} style={style}>
      <div className="vdg-cell">{row.id}</div>
      <div className="vdg-cell">{row.name}</div>
      <div className="vdg-cell">{row.email}</div>
      <div className="vdg-cell">{row.age}</div>
      <div className="vdg-cell">{row.department}</div>
      <div className="vdg-cell">${row.salary.toLocaleString()}</div>
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────────

function VirtualDataGrid() {
  const [filterText, setFilterText] = React.useState('');
  const [debouncedFilter, setDebouncedFilter] = React.useState('');
  const [sortConfig, setSortConfig] = React.useState<SortConfig | null>(null);
  const [scrollTop, setScrollTop] = React.useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);
  const prevRangeRef = useRef<{ start: number; end: number }>({ start: 0, end: 0 });

  useEffect(() => {
    injectStyles();
  }, []);

  // Debounced filter
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedFilter(filterText), 200);
    return () => clearTimeout(timer);
  }, [filterText]);

  // Filter
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

  // Sort
  const sortedData = useMemo(() => {
    if (!sortConfig) return filteredData;
    const { key, direction } = sortConfig;
    const sorted = [...filteredData];
    sorted.sort((a, b) => {
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
    return sorted;
  }, [filteredData, sortConfig]);

  const totalRows = sortedData.length;
  const viewportHeight = 600;
  const totalHeight = totalRows * ROW_HEIGHT;

  // Visible range
  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const endIndex = Math.min(totalRows, Math.ceil((scrollTop + viewportHeight) / ROW_HEIGHT) + OVERSCAN);
  const visibleRows = sortedData.slice(startIndex, endIndex);

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const newScrollTop = e.currentTarget.scrollTop;
    const newStart = Math.max(0, Math.floor(newScrollTop / ROW_HEIGHT) - OVERSCAN);
    const newEnd = Math.min(totalRows, Math.ceil((newScrollTop + viewportHeight) / ROW_HEIGHT) + OVERSCAN);
    if (newStart !== prevRangeRef.current.start || newEnd !== prevRangeRef.current.end) {
      prevRangeRef.current = { start: newStart, end: newEnd };
      setScrollTop(newScrollTop);
    }
  }, [totalRows]);

  const handleSort = useCallback((key: keyof RowData) => {
    setSortConfig(prev => {
      if (!prev || prev.key !== key) return { key, direction: 'asc' };
      if (prev.direction === 'asc') return { key, direction: 'desc' };
      return null;
    });
  }, []);

  return (
    <div className="vdg-root">
      <div className="vdg-toolbar">
        <input
          placeholder="Search by name, email, or department…"
          value={filterText}
          onChange={e => setFilterText(e.target.value)}
        />
        <span className="vdg-info">{totalRows.toLocaleString()} rows</span>
      </div>
      <div className="vdg-container">
        <div className="vdg-header-row">
          {COLUMNS.map(col => (
            <SortableColumnHeader
              key={col.key}
              column={col}
              sortConfig={sortConfig}
              onClick={handleSort}
            />
          ))}
        </div>
        <div
          className="vdg-scroll-container"
          ref={scrollRef}
          onScroll={handleScroll}
        >
          <div className="vdg-spacer" style={{ height: totalHeight }}>
            {visibleRows.map((row, i) => {
              const actualIndex = startIndex + i;
              return (
                <GridRow
                  key={row.id}
                  row={row}
                  isEven={actualIndex % 2 === 0}
                  style={{
                    position: 'absolute',
                    top: actualIndex * ROW_HEIGHT,
                    height: ROW_HEIGHT,
                    width: '100%',
                  }}
                />
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

export default VirtualDataGrid;
