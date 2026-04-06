import React, { useState, useMemo, useCallback, useRef, useEffect } from "react";

// ── CSS Module mock (simulating .module.css scoped classes) ──
const styles: Record<string, React.CSSProperties> = {
  grid: {
    display: "flex",
    flexDirection: "column",
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    fontSize: "13px",
    color: "#333",
    height: "100vh",
    overflow: "hidden",
    backgroundColor: "#f9fafb",
  },
  searchBar: {
    padding: "12px 16px",
    backgroundColor: "#fff",
    borderBottom: "1px solid #e5e7eb",
  },
  searchInput: {
    width: "300px",
    padding: "8px 12px",
    border: "1px solid #d1d5db",
    borderRadius: "6px",
    fontSize: "13px",
    outline: "none",
  },
  headerRow: {
    display: "flex",
    backgroundColor: "#f3f4f6",
    borderBottom: "2px solid #e5e7eb",
    fontWeight: 600,
    fontSize: "12px",
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
    color: "#6b7280",
    position: "sticky" as const,
    top: 0,
    zIndex: 10,
  },
  headerCell: {
    padding: "10px 12px",
    cursor: "pointer",
    userSelect: "none" as const,
    display: "flex",
    alignItems: "center",
    gap: "4px",
  },
  headerCellHover: {
    backgroundColor: "#e5e7eb",
  },
  virtualBody: {
    flex: 1,
    overflowY: "auto" as const,
    position: "relative" as const,
  },
  row: {
    display: "flex",
    borderBottom: "1px solid #f3f4f6",
    backgroundColor: "#fff",
    transition: "background-color 0.1s",
  },
  rowEven: {
    backgroundColor: "#fafbfc",
  },
  cell: {
    padding: "8px 12px",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap" as const,
  },
  sortIndicator: {
    fontSize: "10px",
    marginLeft: "2px",
  },
  statusBar: {
    padding: "8px 16px",
    backgroundColor: "#fff",
    borderTop: "1px solid #e5e7eb",
    fontSize: "12px",
    color: "#6b7280",
    display: "flex",
    justifyContent: "space-between",
  },
};

// ── Data model ──
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

// ── Constants ──
const ROW_HEIGHT = 36;
const OVERSCAN = 5;

const COLUMNS: ColumnDef[] = [
  { key: "id", label: "ID", width: 80, sortable: true },
  { key: "name", label: "Name", width: 180, sortable: true },
  { key: "email", label: "Email", width: 260, sortable: true },
  { key: "department", label: "Department", width: 160, sortable: true },
  { key: "salary", label: "Salary", width: 120, sortable: true },
  { key: "joinDate", label: "Join Date", width: 130, sortable: true },
];

const DEPARTMENTS = [
  "Engineering",
  "Marketing",
  "Sales",
  "Finance",
  "HR",
  "Operations",
  "Design",
  "Legal",
  "Support",
  "Product",
];

// ── Inline mock data generation ──
function generateMockData(count: number): DataRow[] {
  const rows: DataRow[] = [];
  for (let i = 0; i < count; i++) {
    const dept = DEPARTMENTS[i % DEPARTMENTS.length];
    const year = 2015 + (i % 11);
    const month = String((i % 12) + 1).padStart(2, "0");
    const day = String((i % 28) + 1).padStart(2, "0");
    rows.push({
      id: i + 1,
      name: `User_${i + 1}`,
      email: `user_${i + 1}@example.com`,
      department: dept,
      salary: 30000 + ((i * 7) % 70000),
      joinDate: `${year}-${month}-${day}`,
    });
  }
  return rows;
}

const ALL_DATA: DataRow[] = generateMockData(10000);

// ── Debounce helper ──
function useDebounce(value: string, delay: number): string {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

// ── Sort indicator ──
function SortArrow({ direction }: { direction: SortDirection }) {
  if (direction === "asc") return <span style={styles.sortIndicator}>▲</span>;
  if (direction === "desc") return <span style={styles.sortIndicator}>▼</span>;
  return <span style={styles.sortIndicator}>⇅</span>;
}

// ── GridHeader ──
function GridHeader({
  sort,
  onSort,
}: {
  sort: SortState;
  onSort: (key: keyof DataRow) => void;
}) {
  return (
    <div style={styles.headerRow}>
      {COLUMNS.map((col) => (
        <div
          key={col.key}
          style={{ ...styles.headerCell, width: col.width, minWidth: col.width }}
          onClick={() => col.sortable && onSort(col.key)}
        >
          {col.label}
          {col.sortable && <SortArrow direction={sort.column === col.key ? sort.direction : null} />}
        </div>
      ))}
    </div>
  );
}

// ── SearchBar ──
function SearchBar({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div style={styles.searchBar}>
      <input
        style={styles.searchInput}
        placeholder="Search by name or email…"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

// ── GridRow ──
function GridRow({ row, index }: { row: DataRow; index: number }) {
  const isEven = index % 2 === 0;
  return (
    <div style={{ ...styles.row, ...(isEven ? styles.rowEven : {}), height: ROW_HEIGHT }}>
      {COLUMNS.map((col) => {
        let display: string;
        const val = row[col.key];
        if (col.key === "salary") {
          display = `$${(val as number).toLocaleString()}`;
        } else {
          display = String(val);
        }
        return (
          <div key={col.key} style={{ ...styles.cell, width: col.width, minWidth: col.width }}>
            {display}
          </div>
        );
      })}
    </div>
  );
}

// ── Main Component ──
export default function DataGrid() {
  const [filterText, setFilterText] = useState("");
  const [sort, setSort] = useState<SortState>({ column: null, direction: null });
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerHeight, setContainerHeight] = useState(600);
  const rafRef = useRef<number | null>(null);

  const debouncedFilter = useDebounce(filterText, 150);

  // Measure container
  useEffect(() => {
    const measure = () => {
      if (containerRef.current) {
        setContainerHeight(containerRef.current.clientHeight);
      }
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);

  // Filter
  const filteredData = useMemo(() => {
    if (!debouncedFilter) return ALL_DATA;
    const lower = debouncedFilter.toLowerCase();
    return ALL_DATA.filter(
      (row) =>
        row.name.toLowerCase().includes(lower) || row.email.toLowerCase().includes(lower)
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
    Math.floor(scrollTop / ROW_HEIGHT) + Math.ceil(containerHeight / ROW_HEIGHT) + OVERSCAN
  );
  const visibleRows = sortedData.slice(startIndex, endIndex + 1);
  const totalHeight = totalRows * ROW_HEIGHT;
  const topSpacerHeight = startIndex * ROW_HEIGHT;
  const bottomSpacerHeight = Math.max(0, (totalRows - endIndex - 1) * ROW_HEIGHT);

  // Scroll handler with RAF gating
  const handleScroll = useCallback(() => {
    if (rafRef.current !== null) return;
    rafRef.current = requestAnimationFrame(() => {
      if (containerRef.current) {
        setScrollTop(containerRef.current.scrollTop);
      }
      rafRef.current = null;
    });
  }, []);

  // Sort toggle
  const handleSort = useCallback((key: keyof DataRow) => {
    setSort((prev) => {
      if (prev.column !== key) return { column: key, direction: "asc" };
      if (prev.direction === "asc") return { column: key, direction: "desc" };
      if (prev.direction === "desc") return { column: null, direction: null };
      return { column: key, direction: "asc" };
    });
  }, []);

  return (
    <div style={styles.grid}>
      <SearchBar value={filterText} onChange={setFilterText} />
      <GridHeader sort={sort} onSort={handleSort} />
      <div
        ref={containerRef}
        style={styles.virtualBody}
        onScroll={handleScroll}
      >
        <div style={{ height: totalHeight, position: "relative" }}>
          <div style={{ height: topSpacerHeight }} />
          <div style={{ willChange: "transform" }}>
            {visibleRows.map((row, i) => (
              <GridRow key={row.id} row={row} index={startIndex + i} />
            ))}
          </div>
          <div style={{ height: bottomSpacerHeight }} />
        </div>
      </div>
      <div style={styles.statusBar}>
        <span>
          Showing {totalRows.toLocaleString()} of {ALL_DATA.length.toLocaleString()} rows
        </span>
        <span>
          {sort.column
            ? `Sorted by ${sort.column} (${sort.direction})`
            : "Not sorted"}
        </span>
      </div>
    </div>
  );
}
