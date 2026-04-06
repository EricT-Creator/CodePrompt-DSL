import React, { useState, useRef, useCallback, useEffect, useMemo } from "react";

// ── Types ──────────────────────────────────────────────────────────
interface DataRow {
  id: number;
  name: string;
  email: string;
  age: number;
  status: string;
  department: string;
  salary: number;
}

interface ColumnDef {
  id: keyof DataRow;
  title: string;
  width: number;
  sortable: boolean;
}

interface SortState {
  columnId: keyof DataRow;
  direction: "asc" | "desc";
}

// ── Inline styles (CSS Modules emulation) ──────────────────────────
const css: Record<string, React.CSSProperties> = {
  container: {
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    maxWidth: 1000,
    margin: "0 auto",
    border: "1px solid #ddd",
    borderRadius: 8,
    overflow: "hidden",
    background: "#fff",
  },
  searchBar: {
    padding: "12px 16px",
    background: "#f8f9fa",
    borderBottom: "1px solid #ddd",
    display: "flex",
    gap: 12,
    alignItems: "center",
  },
  searchInput: {
    flex: 1,
    padding: "8px 12px",
    border: "1px solid #ccc",
    borderRadius: 4,
    fontSize: 14,
    outline: "none",
  },
  tableHeader: {
    display: "flex",
    background: "#1a1a2e",
    color: "#fff",
    position: "sticky" as const,
    top: 0,
    zIndex: 10,
  },
  headerCell: {
    padding: "10px 12px",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
    userSelect: "none" as const,
    display: "flex",
    alignItems: "center",
    gap: 4,
    borderRight: "1px solid rgba(255,255,255,0.1)",
  },
  bodyContainer: {
    height: 500,
    overflow: "auto",
    position: "relative" as const,
  },
  row: {
    display: "flex",
    borderBottom: "1px solid #f0f0f0",
  },
  rowEven: {
    background: "#fafbfc",
  },
  cell: {
    padding: "8px 12px",
    fontSize: 13,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap" as const,
    borderRight: "1px solid #f0f0f0",
  },
  statusBadge: {
    display: "inline-block",
    padding: "2px 8px",
    borderRadius: 12,
    fontSize: 11,
    fontWeight: 600,
  },
  info: {
    padding: "8px 16px",
    background: "#f8f9fa",
    borderTop: "1px solid #ddd",
    fontSize: 12,
    color: "#666",
    display: "flex",
    justifyContent: "space-between",
  },
};

const STATUS_COLORS: Record<string, string> = {
  Active: "#4caf50",
  Inactive: "#9e9e9e",
  Pending: "#ff9800",
};

// ── Mock data generation ───────────────────────────────────────────
const DEPARTMENTS = ["Engineering", "Marketing", "Sales", "Design", "Finance", "HR", "Legal", "Support"];
const STATUSES = ["Active", "Inactive", "Pending"];

function generateMockData(count: number): DataRow[] {
  const data: DataRow[] = [];
  for (let i = 0; i < count; i++) {
    data.push({
      id: i + 1,
      name: `User ${i + 1}`,
      email: `user${i + 1}@example.com`,
      age: 20 + (i % 45),
      status: STATUSES[i % 3],
      department: DEPARTMENTS[i % DEPARTMENTS.length],
      salary: 40000 + ((i * 137) % 80000),
    });
  }
  return data;
}

// ── Column definitions ─────────────────────────────────────────────
const COLUMNS: ColumnDef[] = [
  { id: "id", title: "ID", width: 60, sortable: true },
  { id: "name", title: "Name", width: 160, sortable: true },
  { id: "email", title: "Email", width: 220, sortable: true },
  { id: "age", title: "Age", width: 70, sortable: true },
  { id: "department", title: "Department", width: 130, sortable: true },
  { id: "status", title: "Status", width: 100, sortable: true },
  { id: "salary", title: "Salary", width: 110, sortable: true },
];

const ROW_HEIGHT = 36;
const OVERSCAN = 5;
const TOTAL_ROWS = 10000;

// ── Component ──────────────────────────────────────────────────────
const VirtualDataGrid: React.FC = () => {
  const [allData] = useState<DataRow[]>(() => generateMockData(TOTAL_ROWS));
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortState | null>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number>(0);

  // Filter + sort
  const processedData = useMemo(() => {
    let data = allData;

    if (search.trim()) {
      const q = search.toLowerCase();
      data = data.filter(
        (r) =>
          r.name.toLowerCase().includes(q) ||
          r.email.toLowerCase().includes(q) ||
          r.department.toLowerCase().includes(q) ||
          r.status.toLowerCase().includes(q)
      );
    }

    if (sort) {
      const { columnId, direction } = sort;
      data = [...data].sort((a, b) => {
        const va = a[columnId];
        const vb = b[columnId];
        let cmp = 0;
        if (typeof va === "number" && typeof vb === "number") cmp = va - vb;
        else cmp = String(va).localeCompare(String(vb));
        return direction === "asc" ? cmp : -cmp;
      });
    }

    return data;
  }, [allData, search, sort]);

  // Viewport calculation
  const containerHeight = 500;
  const totalHeight = processedData.length * ROW_HEIGHT;
  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const visibleCount = Math.ceil(containerHeight / ROW_HEIGHT) + OVERSCAN * 2;
  const endIndex = Math.min(processedData.length - 1, startIndex + visibleCount);

  const visibleRows = processedData.slice(startIndex, endIndex + 1);
  const topPad = startIndex * ROW_HEIGHT;
  const bottomPad = Math.max(0, totalHeight - (endIndex + 1) * ROW_HEIGHT);

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget;
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => {
      setScrollTop(target.scrollTop);
    });
  }, []);

  const handleSort = useCallback(
    (colId: keyof DataRow) => {
      setSort((prev) => {
        if (prev && prev.columnId === colId) {
          if (prev.direction === "asc") return { columnId: colId, direction: "desc" };
          return null;
        }
        return { columnId: colId, direction: "asc" };
      });
    },
    []
  );

  useEffect(() => {
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  const sortIndicator = (colId: keyof DataRow): string => {
    if (!sort || sort.columnId !== colId) return "";
    return sort.direction === "asc" ? " ▲" : " ▼";
  };

  return (
    <div style={css.container}>
      {/* Search */}
      <div style={css.searchBar}>
        <input
          style={css.searchInput}
          placeholder="Search by name, email, department, status…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <span style={{ fontSize: 12, color: "#888" }}>{processedData.length.toLocaleString()} rows</span>
      </div>

      {/* Header */}
      <div style={css.tableHeader}>
        {COLUMNS.map((col) => (
          <div
            key={col.id}
            style={{ ...css.headerCell, width: col.width, minWidth: col.width }}
            onClick={() => col.sortable && handleSort(col.id)}
          >
            {col.title}
            {sortIndicator(col.id)}
          </div>
        ))}
      </div>

      {/* Virtual body */}
      <div style={css.bodyContainer} onScroll={handleScroll} ref={containerRef}>
        <div style={{ height: topPad }} />
        {visibleRows.map((row, i) => (
          <div key={row.id} style={{ ...css.row, height: ROW_HEIGHT, ...((startIndex + i) % 2 === 0 ? css.rowEven : {}) }}>
            {COLUMNS.map((col) => {
              const val = row[col.id];
              return (
                <div key={col.id} style={{ ...css.cell, width: col.width, minWidth: col.width, lineHeight: `${ROW_HEIGHT - 16}px` }}>
                  {col.id === "status" ? (
                    <span style={{ ...css.statusBadge, background: STATUS_COLORS[val as string] ?? "#999", color: "#fff" }}>
                      {val}
                    </span>
                  ) : col.id === "salary" ? (
                    `$${(val as number).toLocaleString()}`
                  ) : (
                    String(val)
                  )}
                </div>
              );
            })}
          </div>
        ))}
        <div style={{ height: bottomPad }} />
      </div>

      {/* Footer info */}
      <div style={css.info}>
        <span>
          Showing rows {startIndex + 1}–{Math.min(endIndex + 1, processedData.length)} of {processedData.length.toLocaleString()}
        </span>
        <span>Total: {TOTAL_ROWS.toLocaleString()} | Rendered: {visibleRows.length}</span>
      </div>
    </div>
  );
};

export default VirtualDataGrid;
