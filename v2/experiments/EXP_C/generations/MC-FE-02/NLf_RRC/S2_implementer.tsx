import React, { useRef, useCallback, useMemo, useEffect } from 'react';

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
const STYLE_ID = 'vdg-styles';
const P = 'vdg';

const DEPARTMENTS = ['Engineering', 'Marketing', 'Sales', 'HR', 'Finance', 'Operations', 'Legal', 'Support', 'Product', 'Design'];
const FIRST_NAMES = ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda', 'William', 'Elizabeth', 'David', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica', 'Thomas', 'Sarah', 'Charles', 'Karen'];
const LAST_NAMES = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin'];

// ── Styles ──────────────────────────────────────────────────────────────────

const cssText = `
.${P}-container {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  max-width: 1100px;
  margin: 20px auto;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  overflow: hidden;
}
.${P}-toolbar {
  display: flex;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid #e5e7eb;
  background: #fafbfc;
}
.${P}-toolbar-title {
  font-size: 18px;
  font-weight: 700;
  color: #1a1a2e;
  margin-right: auto;
}
.${P}-search {
  padding: 8px 14px;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  font-size: 13px;
  width: 260px;
  outline: none;
  transition: border-color 0.15s;
}
.${P}-search:focus {
  border-color: #4f46e5;
}
.${P}-row-count {
  font-size: 12px;
  color: #888;
  margin-left: 12px;
}
.${P}-header-row {
  display: flex;
  background: #f3f4f6;
  border-bottom: 2px solid #e5e7eb;
  position: sticky;
  top: 0;
  z-index: 2;
}
.${P}-header-cell {
  flex: 1;
  padding: 10px 14px;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #555;
  cursor: pointer;
  user-select: none;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: background 0.1s;
}
.${P}-header-cell:hover {
  background: #e9ebee;
}
.${P}-header-cell-id { flex: 0.5; }
.${P}-header-cell-name { flex: 1.2; }
.${P}-header-cell-email { flex: 1.5; }
.${P}-header-cell-age { flex: 0.5; }
.${P}-header-cell-dept { flex: 1; }
.${P}-header-cell-salary { flex: 0.8; }
.${P}-sort-indicator {
  font-size: 11px;
  color: #4f46e5;
}
.${P}-scroll-container {
  height: ${VIEWPORT_HEIGHT}px;
  overflow-y: auto;
  position: relative;
}
.${P}-spacer {
  position: relative;
}
.${P}-row {
  display: flex;
  position: absolute;
  left: 0;
  right: 0;
  height: ${ROW_HEIGHT}px;
  align-items: center;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.1s;
}
.${P}-row:hover {
  background: #f5f7ff;
}
.${P}-row-even {
  background: #fafbfc;
}
.${P}-cell {
  flex: 1;
  padding: 0 14px;
  font-size: 13px;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.${P}-cell-id { flex: 0.5; color: #999; }
.${P}-cell-name { flex: 1.2; font-weight: 500; }
.${P}-cell-email { flex: 1.5; color: #666; }
.${P}-cell-age { flex: 0.5; text-align: center; }
.${P}-cell-dept { flex: 1; }
.${P}-cell-salary { flex: 0.8; font-variant-numeric: tabular-nums; }
`;

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
  { key: 'id', label: 'ID', headerClass: `${P}-header-cell-id`, cellClass: `${P}-cell-id` },
  { key: 'name', label: 'Name', headerClass: `${P}-header-cell-name`, cellClass: `${P}-cell-name` },
  { key: 'email', label: 'Email', headerClass: `${P}-header-cell-email`, cellClass: `${P}-cell-email` },
  { key: 'age', label: 'Age', headerClass: `${P}-header-cell-age`, cellClass: `${P}-cell-age` },
  { key: 'department', label: 'Department', headerClass: `${P}-header-cell-dept`, cellClass: `${P}-cell-dept` },
  {
    key: 'salary',
    label: 'Salary',
    headerClass: `${P}-header-cell-salary`,
    cellClass: `${P}-cell-salary`,
    format: (v: number) => `$${v.toLocaleString()}`,
  },
];

// ── Sub-Components ──────────────────────────────────────────────────────────

const GridToolbar: React.FC<{
  filterText: string;
  onFilterChange: (text: string) => void;
  rowCount: number;
}> = ({ filterText, onFilterChange, rowCount }) => (
  <div className={`${P}-toolbar`}>
    <div className={`${P}-toolbar-title`}>Data Grid</div>
    <input
      className={`${P}-search`}
      placeholder="Search by name, email, or department..."
      value={filterText}
      onChange={e => onFilterChange(e.target.value)}
    />
    <div className={`${P}-row-count`}>{rowCount.toLocaleString()} rows</div>
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
      className={`${P}-header-cell ${col.headerClass}`}
      onClick={() => onSort(col.key)}
    >
      {col.label}
      {indicator && <span className={`${P}-sort-indicator`}>{indicator}</span>}
    </div>
  );
};

const GridHeader: React.FC<{
  sortConfig: SortConfig | null;
  onSort: (key: keyof RowData) => void;
}> = ({ sortConfig, onSort }) => (
  <div className={`${P}-header-row`}>
    {COLUMNS.map(col => (
      <SortableColumnHeader key={col.key} col={col} sortConfig={sortConfig} onSort={onSort} />
    ))}
  </div>
);

const GridRow: React.FC<{ row: RowData; top: number; even: boolean }> = ({ row, top, even }) => (
  <div
    className={`${P}-row ${even ? `${P}-row-even` : ''}`}
    style={{ top }}
  >
    {COLUMNS.map(col => (
      <div key={col.key} className={`${P}-cell ${col.cellClass}`}>
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

  // Inject styles
  useEffect(() => {
    if (!document.getElementById(STYLE_ID)) {
      const style = document.createElement('style');
      style.id = STYLE_ID;
      style.textContent = cssText;
      document.head.appendChild(style);
    }
    return () => {
      const el = document.getElementById(STYLE_ID);
      if (el) el.remove();
    };
  }, []);

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
    <div className={`${P}-container`}>
      <GridToolbar
        filterText={filterText}
        onFilterChange={setFilterText}
        rowCount={totalRows}
      />
      <GridHeader sortConfig={sortConfig} onSort={handleSort} />
      <div
        ref={scrollRef}
        className={`${P}-scroll-container`}
        onScroll={handleScroll}
      >
        <div className={`${P}-spacer`} style={{ height: totalHeight }}>
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
