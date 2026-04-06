import React, { useState, useMemo, useCallback, useRef, useEffect } from "react";

// ─── CSS Modules mock (inline scoped class names) ───
const styles: Record<string, string> = {
  grid: "grid",
  searchBar: "searchBar",
  searchInput: "searchInput",
  header: "header",
  headerCell: "headerCell",
  headerCellSortable: "headerCellSortable",
  sortIndicator: "sortIndicator",
  virtualBody: "virtualBody",
  row: "row",
  rowAlt: "rowAlt",
  cell: "cell",
  spacer: "spacer",
  info: "info",
};

const styleSheet = `
.grid {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
  max-width: 960px;
  margin: 24px auto;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.searchBar {
  padding: 12px 16px;
  border-bottom: 1px solid #e0e0e0;
  background: #fafafa;
}
.searchInput {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 14px;
  outline: none;
  box-sizing: border-box;
}
.searchInput:focus {
  border-color: #1890ff;
}
.header {
  display: flex;
  background: #fafafa;
  border-bottom: 2px solid #e0e0e0;
  position: sticky;
  top: 0;
  z-index: 1;
}
.headerCell {
  padding: 10px 12px;
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #666;
  flex-shrink: 0;
  user-select: none;
}
.headerCellSortable {
  cursor: pointer;
}
.headerCellSortable:hover {
  color: #1890ff;
}
.sortIndicator {
  margin-left: 4px;
  font-size: 10px;
}
.virtualBody {
  overflow-y: auto;
  position: relative;
}
.row {
  display: flex;
  border-bottom: 1px solid #f0f0f0;
}
.rowAlt {
  background: #fafafa;
}
.cell {
  padding: 8px 12px;
  font-size: 13px;
  color: #333;
  flex-shrink: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.info {
  padding: 8px 16px;
  font-size: 12px;
  color: #999;
  background: #fafafa;
  border-top: 1px solid #e0e0e0;
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

type SortDirection = "asc" | "desc" | null;

interface SortState {
  column: keyof DataRow | null;
  direction: SortDirection;
}

// ─── Constants ───
const ROW_HEIGHT = 36;
const OVERSCAN = 5;
const CONTAINER_HEIGHT = 600;

const COLUMNS: ColumnDef[] = [
  { key: "id", label: "ID", width: 80, sortable: true },
  { key: "name", label: "Name", width: 180, sortable: true },
  { key: "email", label: "Email", width: 240, sortable: true },
  { key: "department", label: "Dept", width: 140, sortable: true },
  { key: "salary", label: "Salary", width: 120, sortable: true },
  { key: "joinDate", label: "Join Date", width: 140, sortable: true },
];

const DEPARTMENTS = ["Engineering", "Marketing", "Sales", "Design", "Finance", "HR", "Product", "Support"];

// ─── Inline Mock Data ───
function generateMockData(count: number): DataRow[] {
  const rows: DataRow[] = [];
  for (let i = 0; i < count; i++) {
    const year = 2015 + (i % 10);
    const month = String((i % 12) + 1).padStart(2, "0");
    const day = String((i % 28) + 1).padStart(2, "0");
    rows.push({
      id: i + 1,
      name: `User_${i + 1}`,
      email: `user_${i + 1}@example.com`,
      department: DEPARTMENTS[i % DEPARTMENTS.length],
      salary: 30000 + ((i * 7) % 70000),
      joinDate: `${year}-${month}-${day}`,
    });
  }
  return rows;
}

const ALL_DATA: DataRow[] = generateMockData(10000);

// ─── Debounce ───
function useDebounce(value: string, delay: number): string {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debouncedValue;
}

// ─── Sub-components ───
interface SearchBarProps {
  value: string;
  onChange: (v: string) => void;
}

function SearchBar({ value, onChange }: SearchBarProps) {
  return (
    <div className={styles.searchBar}>
      <input
        className={styles.searchInput}
        placeholder="Search by name or email…"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

interface GridHeaderProps {
  columns: ColumnDef[];
  sort: SortState;
  onSort: (key: keyof DataRow) => void;
}

function GridHeader({ columns, sort, onSort }: GridHeaderProps) {
  return (
    <div className={styles.header}>
      {columns.map((col) => (
        <div
          key={col.key}
          className={`${styles.headerCell} ${col.sortable ? styles.headerCellSortable : ""}`}
          style={{ width: col.width }}
          onClick={() => col.sortable && onSort(col.key)}
        >
          {col.label}
          {sort.column === col.key && sort.direction && (
            <span className={styles.sortIndicator}>
              {sort.direction === "asc" ? "▲" : "▼"}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

interface GridRowProps {
  row: DataRow;
  columns: ColumnDef[];
  index: number;
}

function GridRow({ row, columns, index }: GridRowProps) {
  return (
    <div className={`${styles.row} ${index % 2 === 1 ? styles.rowAlt : ""}`}>
      {columns.map((col) => (
        <div key={col.key} className={styles.cell} style={{ width: col.width }}>
          {col.key === "salary" ? `$${(row[col.key] as number).toLocaleString()}` : String(row[col.key])}
        </div>
      ))}
    </div>
  );
}

// ─── Main Component ───
export default function DataGrid(): React.ReactElement {
  const [filterText, setFilterText] = useState("");
  const [sort, setSort] = useState<SortState>({ column: null, direction: null });
  const [scrollTop, setScrollTop] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number>(0);

  const debouncedFilter = useDebounce(filterText, 150);

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
    const dir = sort.direction === "asc" ? 1 : -1;
    return [...filteredData].sort((a, b) => {
      const aVal = a[col];
      const bVal = b[col];
      if (typeof aVal === "number" && typeof bVal === "number") {
        return (aVal - bVal) * dir;
      }
      return String(aVal).localeCompare(String(bVal)) * dir;
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
  const topSpacer = startIndex * ROW_HEIGHT;
  const bottomSpacer = Math.max(0, (totalRows - endIndex - 1) * ROW_HEIGHT);

  const handleScroll = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => {
      if (scrollRef.current) {
        setScrollTop(scrollRef.current.scrollTop);
      }
    });
  }, []);

  const handleSort = useCallback((key: keyof DataRow) => {
    setSort((prev) => {
      if (prev.column !== key) return { column: key, direction: "asc" };
      if (prev.direction === "asc") return { column: key, direction: "desc" };
      if (prev.direction === "desc") return { column: null, direction: null };
      return { column: key, direction: "asc" };
    });
  }, []);

  return (
    <>
      <style>{styleSheet}</style>
      <div className={styles.grid}>
        <SearchBar value={filterText} onChange={setFilterText} />
        <GridHeader columns={COLUMNS} sort={sort} onSort={handleSort} />
        <div
          ref={scrollRef}
          className={styles.virtualBody}
          style={{ height: CONTAINER_HEIGHT }}
          onScroll={handleScroll}
        >
          <div style={{ height: totalRows * ROW_HEIGHT, position: "relative" }}>
            <div style={{ height: topSpacer }} />
            <div style={{ willChange: "transform" }}>
              {visibleRows.map((row, i) => (
                <GridRow
                  key={row.id}
                  row={row}
                  columns={COLUMNS}
                  index={startIndex + i}
                />
              ))}
            </div>
            <div style={{ height: bottomSpacer }} />
          </div>
        </div>
        <div className={styles.info}>
          Showing {totalRows.toLocaleString()} rows
          {debouncedFilter && ` (filtered from ${ALL_DATA.length.toLocaleString()})`}
        </div>
      </div>
    </>
  );
}
