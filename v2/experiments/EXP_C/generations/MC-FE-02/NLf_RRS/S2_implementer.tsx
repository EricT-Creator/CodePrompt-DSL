import React, { useRef, useEffect, useCallback, useMemo, useState } from 'react';

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
const PREFIX = 'vdg_';

const DEPARTMENTS = ['Engineering', 'Marketing', 'Sales', 'HR', 'Finance', 'Design', 'Operations', 'Legal', 'Support', 'Research'];
const FIRST_NAMES = ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda', 'David', 'Elizabeth', 'William', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica', 'Thomas', 'Sarah', 'Charles', 'Karen'];
const LAST_NAMES = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin'];

// ── Style injection ─────────────────────────────────────────────────────────

const cssText = `
.${PREFIX}container {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  max-width: 1000px;
  margin: 24px auto;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  overflow: hidden;
}
.${PREFIX}toolbar {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #eee;
  gap: 12px;
}
.${PREFIX}searchInput {
  flex: 1;
  padding: 8px 14px;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
}
.${PREFIX}searchInput:focus {
  border-color: #5b6abf;
}
.${PREFIX}info {
  font-size: 13px;
  color: #888;
}
.${PREFIX}headerRow {
  display: flex;
  background: #f8f9fa;
  border-bottom: 2px solid #e0e0e0;
  position: sticky;
  top: 0;
  z-index: 1;
}
.${PREFIX}headerCell {
  flex: 1;
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 700;
  color: #555;
  cursor: pointer;
  user-select: none;
  display: flex;
  align-items: center;
  gap: 4px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.${PREFIX}headerCell:hover {
  background: #eef0f4;
}
.${PREFIX}sortIcon {
  font-size: 11px;
  color: #aaa;
}
.${PREFIX}sortIconActive {
  color: #5b6abf;
}
.${PREFIX}scrollContainer {
  height: ${VIEWPORT_HEIGHT}px;
  overflow-y: auto;
  position: relative;
}
.${PREFIX}spacer {
  position: relative;
  width: 100%;
}
.${PREFIX}row {
  display: flex;
  position: absolute;
  width: 100%;
  left: 0;
  border-bottom: 1px solid #f0f0f0;
}
.${PREFIX}rowEven {
  background: #fafbfc;
}
.${PREFIX}rowOdd {
  background: #fff;
}
.${PREFIX}cell {
  flex: 1;
  padding: 8px 12px;
  font-size: 13px;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.${PREFIX}cellId {
  max-width: 70px;
  flex: 0 0 70px;
  color: #999;
}
.${PREFIX}cellSalary {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
`;

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
  { key: 'id', label: 'ID', className: `${PREFIX}cellId` },
  { key: 'name', label: 'Name' },
  { key: 'email', label: 'Email' },
  { key: 'age', label: 'Age' },
  { key: 'department', label: 'Dept' },
  { key: 'salary', label: 'Salary', className: `${PREFIX}cellSalary` },
];

// ── Sub-components ──────────────────────────────────────────────────────────

const GridToolbar: React.FC<{ filterText: string; onChange: (v: string) => void; count: number }> = ({ filterText, onChange, count }) => (
  <div className={`${PREFIX}toolbar`}>
    <input
      className={`${PREFIX}searchInput`}
      placeholder="Search by name, email, department..."
      value={filterText}
      onChange={e => onChange(e.target.value)}
    />
    <span className={`${PREFIX}info`}>{count.toLocaleString()} rows</span>
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
    <div className={`${PREFIX}headerCell`} onClick={() => onSort(col.key)}>
      {col.label}
      <span className={`${PREFIX}sortIcon ${isActive ? `${PREFIX}sortIconActive` : ''}`}>{icon}</span>
    </div>
  );
};

const GridRow: React.FC<{ row: RowData; index: number; top: number }> = ({ row, index, top }) => (
  <div
    className={`${PREFIX}row ${index % 2 === 0 ? `${PREFIX}rowEven` : `${PREFIX}rowOdd`}`}
    style={{ top, height: ROW_HEIGHT }}
  >
    <div className={`${PREFIX}cell ${PREFIX}cellId`}>{row.id}</div>
    <div className={`${PREFIX}cell`}>{row.name}</div>
    <div className={`${PREFIX}cell`}>{row.email}</div>
    <div className={`${PREFIX}cell`}>{row.age}</div>
    <div className={`${PREFIX}cell`}>{row.department}</div>
    <div className={`${PREFIX}cell ${PREFIX}cellSalary`}>${row.salary.toLocaleString()}</div>
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
  const styleRef = useRef<HTMLStyleElement | null>(null);

  // Inject styles
  useEffect(() => {
    const style = document.createElement('style');
    style.textContent = cssText;
    document.head.appendChild(style);
    styleRef.current = style;
    return () => { style.remove(); };
  }, []);

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
    <div className={`${PREFIX}container`}>
      <GridToolbar filterText={filterText} onChange={handleFilterChange} count={totalRows} />
      <div className={`${PREFIX}headerRow`}>
        {COLUMNS.map(col => (
          <SortableColumnHeader key={col.key} col={col} sortConfig={sortConfig} onSort={handleSort} />
        ))}
      </div>
      <div className={`${PREFIX}scrollContainer`} ref={scrollRef} onScroll={handleScroll}>
        <div className={`${PREFIX}spacer`} style={{ height: totalHeight }}>
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
