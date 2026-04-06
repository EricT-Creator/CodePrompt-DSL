import React, { useState, useMemo, useCallback, useRef, useEffect } from 'react';

// ─── CSS Modules mock (inline scoped class names) ───
const styles: Record<string, string> = {
  grid: 'grid',
  searchBar: 'searchBar',
  searchInput: 'searchInput',
  headerRow: 'headerRow',
  headerCell: 'headerCell',
  headerCellSortable: 'headerCellSortable',
  sortIndicator: 'sortIndicator',
  virtualBody: 'virtualBody',
  row: 'row',
  rowEven: 'rowEven',
  cell: 'cell',
  resultCount: 'resultCount',
};

const STYLE_CONTENT = `
.grid {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  overflow: hidden;
  margin: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.searchBar {
  padding: 12px 16px;
  border-bottom: 1px solid #e8e8e8;
  background: #fafafa;
  display: flex;
  align-items: center;
  gap: 12px;
}
.searchInput {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 14px;
  outline: none;
}
.searchInput:focus {
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24,144,255,0.1);
}
.resultCount {
  font-size: 13px;
  color: #888;
  white-space: nowrap;
}
.headerRow {
  display: flex;
  background: #fafafa;
  border-bottom: 2px solid #e8e8e8;
  position: sticky;
  top: 0;
  z-index: 1;
}
.headerCell {
  padding: 10px 12px;
  font-weight: 600;
  font-size: 13px;
  color: #333;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-sizing: border-box;
  flex-shrink: 0;
  user-select: none;
}
.headerCellSortable {
  cursor: pointer;
}
.headerCellSortable:hover {
  background: #f0f0f0;
}
.sortIndicator {
  margin-left: 4px;
  font-size: 12px;
}
.virtualBody {
  overflow-y: auto;
  position: relative;
}
.row {
  display: flex;
  border-bottom: 1px solid #f0f0f0;
  will-change: transform;
}
.rowEven {
  background: #fafafa;
}
.row:hover {
  background: #e6f7ff;
}
.cell {
  padding: 8px 12px;
  font-size: 13px;
  color: #555;
  box-sizing: border-box;
  flex-shrink: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
`;

// ─── Types ───
interface DataRow {
  id: number;
  name: string;
  email: string;
  department: string;
  salary: number;
  joinDate: string;
}

interface ColumnDef {
  key: keyof DataRow;
  label: string;
  width: number;
  sortable: boolean;
}

type SortDirection = 'asc' | 'desc' | null;

interface SortState {
  column: keyof DataRow | null;
  direction: SortDirection;
}

// ─── Constants ───
const ROW_HEIGHT = 36;
const OVERSCAN = 5;
const CONTAINER_HEIGHT = 600;
const DEBOUNCE_MS = 150;

const COLUMNS: ColumnDef[] = [
  { key: 'id', label: 'ID', width: 80, sortable: true },
  { key: 'name', label: 'Name', width: 180, sortable: true },
  { key: 'email', label: 'Email', width: 250, sortable: true },
  { key: 'department', label: 'Department', width: 150, sortable: true },
  { key: 'salary', label: 'Salary', width: 120, sortable: true },
  { key: 'joinDate', label: 'Join Date', width: 130, sortable: true },
];

const DEPARTMENTS = ['Engineering', 'Marketing', 'Sales', 'HR', 'Finance', 'Operations', 'Design', 'Legal'];

// ─── Inline mock data generation ───
function generateMockData(count: number): DataRow[] {
  const rows: DataRow[] = [];
  for (let i = 0; i < count; i++) {
    const year = 2015 + (i % 10);
    const month = String(1 + (i % 12)).padStart(2, '0');
    const day = String(1 + (i % 28)).padStart(2, '0');
    rows.push({
      id: i + 1,
      name: `User_${i + 1}`,
      email: `user${i + 1}@example.com`,
      department: DEPARTMENTS[i % DEPARTMENTS.length],
      salary: 30000 + ((i * 7) % 70000),
      joinDate: `${year}-${month}-${day}`,
    });
  }
  return rows;
}

const ALL_DATA: DataRow[] = generateMockData(10000);

// ─── Debounce helper ───
function useDebounce(value: string, delay: number): string {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debouncedValue;
}

// ─── Sub-components (internal) ───

function SearchBar({
  value,
  onChange,
  resultCount,
}: {
  value: string;
  onChange: (v: string) => void;
  resultCount: number;
}) {
  return (
    <div className={styles.searchBar}>
      <input
        className={styles.searchInput}
        type="text"
        placeholder="Search by name or email..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <span className={styles.resultCount}>{resultCount.toLocaleString()} results</span>
    </div>
  );
}

function GridHeader({
  columns,
  sort,
  onSortToggle,
}: {
  columns: ColumnDef[];
  sort: SortState;
  onSortToggle: (key: keyof DataRow) => void;
}) {
  return (
    <div className={styles.headerRow}>
      {columns.map((col) => (
        <div
          key={col.key}
          className={`${styles.headerCell} ${col.sortable ? styles.headerCellSortable : ''}`}
          style={{ width: col.width }}
          onClick={() => col.sortable && onSortToggle(col.key)}
        >
          {col.label}
          {sort.column === col.key && sort.direction && (
            <span className={styles.sortIndicator}>
              {sort.direction === 'asc' ? '▲' : '▼'}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

function GridRow({ row, index, columns }: { row: DataRow; index: number; columns: ColumnDef[] }) {
  return (
    <div className={`${styles.row} ${index % 2 === 0 ? styles.rowEven : ''}`}>
      {columns.map((col) => (
        <div key={col.key} className={styles.cell} style={{ width: col.width }}>
          {col.key === 'salary' ? `$${(row[col.key] as number).toLocaleString()}` : String(row[col.key])}
        </div>
      ))}
    </div>
  );
}

// ─── Main Component ───
export default function DataGrid(): React.ReactElement {
  const [filterText, setFilterText] = useState('');
  const [sort, setSort] = useState<SortState>({ column: null, direction: null });
  const [scrollTop, setScrollTop] = useState(0);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number | null>(null);

  const debouncedFilter = useDebounce(filterText, DEBOUNCE_MS);

  // Filter
  const filteredData = useMemo(() => {
    if (!debouncedFilter) return ALL_DATA;
    const lower = debouncedFilter.toLowerCase();
    return ALL_DATA.filter(
      (row) =>
        row.name.toLowerCase().includes(lower) ||
        row.email.toLowerCase().includes(lower)
    );
  }, [debouncedFilter]);

  // Sort
  const sortedData = useMemo(() => {
    if (!sort.column || !sort.direction) return filteredData;
    const col = sort.column;
    const dir = sort.direction === 'asc' ? 1 : -1;

    return [...filteredData].sort((a, b) => {
      const va = a[col];
      const vb = b[col];
      if (typeof va === 'number' && typeof vb === 'number') {
        return (va - vb) * dir;
      }
      return String(va).localeCompare(String(vb)) * dir;
    });
  }, [filteredData, sort]);

  // Virtual range
  const totalRows = sortedData.length;
  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const endIndex = Math.min(
    totalRows - 1,
    Math.floor(scrollTop / ROW_HEIGHT) + Math.ceil(CONTAINER_HEIGHT / ROW_HEIGHT) + OVERSCAN
  );
  const visibleRows = sortedData.slice(startIndex, endIndex + 1);
  const topSpacerHeight = startIndex * ROW_HEIGHT;
  const bottomSpacerHeight = Math.max(0, (totalRows - endIndex - 1) * ROW_HEIGHT);

  // Scroll handler
  const handleScroll = useCallback(() => {
    if (rafRef.current !== null) return;
    rafRef.current = requestAnimationFrame(() => {
      if (scrollContainerRef.current) {
        setScrollTop(scrollContainerRef.current.scrollTop);
      }
      rafRef.current = null;
    });
  }, []);

  // Sort toggle
  const handleSortToggle = useCallback((key: keyof DataRow) => {
    setSort((prev) => {
      if (prev.column !== key) return { column: key, direction: 'asc' };
      if (prev.direction === 'asc') return { column: key, direction: 'desc' };
      if (prev.direction === 'desc') return { column: null, direction: null };
      return { column: key, direction: 'asc' };
    });
  }, []);

  // Reset scroll on filter/sort change
  useEffect(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = 0;
      setScrollTop(0);
    }
  }, [debouncedFilter, sort]);

  return (
    <>
      <style>{STYLE_CONTENT}</style>
      <div className={styles.grid}>
        <SearchBar value={filterText} onChange={setFilterText} resultCount={totalRows} />
        <GridHeader columns={COLUMNS} sort={sort} onSortToggle={handleSortToggle} />
        <div
          ref={scrollContainerRef}
          className={styles.virtualBody}
          style={{ height: CONTAINER_HEIGHT }}
          onScroll={handleScroll}
        >
          <div style={{ height: topSpacerHeight }} />
          {visibleRows.map((row, i) => (
            <GridRow key={row.id} row={row} index={startIndex + i} columns={COLUMNS} />
          ))}
          <div style={{ height: bottomSpacerHeight }} />
        </div>
      </div>
    </>
  );
}
