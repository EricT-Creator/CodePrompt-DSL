import React, { useRef, useState, useMemo, useCallback, useEffect } from "react";

// ─── Types ───

interface ColumnDef {
  key: string;
  title: string;
  width: number;
  sortable: boolean;
  dataType: "string" | "number" | "date";
}

interface Row {
  id: number;
  name: string;
  email: string;
  age: number;
  department: string;
  salary: number;
  joinDate: string;
  [key: string]: unknown;
}

type SortDirection = "asc" | "desc" | null;

interface SortConfig {
  key: string | null;
  direction: SortDirection;
}

interface VisibleRange {
  startIndex: number;
  endIndex: number;
  offsetY: number;
}

// ─── CSS Modules (inline object since single file) ───

const cls: Record<string, React.CSSProperties> = {
  container: {
    fontFamily: "system-ui, sans-serif",
    border: "1px solid #d9d9d9",
    borderRadius: 6,
    overflow: "hidden",
    background: "#fff",
  },
  filterRow: {
    padding: "8px 12px",
    borderBottom: "1px solid #e8e8e8",
    background: "#fafafa",
  },
  filterInput: {
    width: "100%",
    padding: "6px 10px",
    border: "1px solid #d9d9d9",
    borderRadius: 4,
    fontSize: 13,
    boxSizing: "border-box" as const,
  },
  headerRow: {
    display: "flex",
    borderBottom: "2px solid #e8e8e8",
    background: "#fafafa",
    fontWeight: 600,
    fontSize: 13,
    position: "sticky" as const,
    top: 0,
    zIndex: 1,
  },
  headerCell: {
    padding: "8px 12px",
    cursor: "pointer",
    userSelect: "none" as const,
    borderRight: "1px solid #f0f0f0",
    display: "flex",
    alignItems: "center",
    gap: 4,
  },
  bodyContainer: {
    overflow: "auto",
    position: "relative" as const,
  },
  row: {
    display: "flex",
    borderBottom: "1px solid #f0f0f0",
  },
  rowEven: {
    background: "#fafafa",
  },
  cell: {
    padding: "6px 12px",
    fontSize: 13,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap" as const,
    borderRight: "1px solid #f5f5f5",
  },
  info: {
    padding: "6px 12px",
    fontSize: 12,
    color: "#999",
    borderTop: "1px solid #e8e8e8",
    display: "flex",
    justifyContent: "space-between",
  },
};

// ─── Constants ───

const ROW_HEIGHT = 36;
const OVERSCAN = 5;
const TOTAL_ROWS = 10000;
const VIEWPORT_HEIGHT = 500;

// ─── Mock data ───

const FIRST_NAMES = ["Alice", "Bob", "Carol", "David", "Eve", "Frank", "Grace", "Hank", "Ivy", "Jack", "Kate", "Leo", "Mona", "Nick", "Olive", "Paul", "Quinn", "Rose", "Sam", "Tina"];
const LAST_NAMES = ["Smith", "Johnson", "Brown", "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin", "Garcia", "Clark", "Lewis", "Lee", "Walker", "Hall", "Allen", "Young", "King", "Wright"];
const DEPARTMENTS = ["Engineering", "Marketing", "Sales", "HR", "Finance", "Design", "Product", "Support", "Legal", "Operations"];

function generateMockData(count: number): Row[] {
  const rows: Row[] = [];
  for (let i = 0; i < count; i++) {
    const first = FIRST_NAMES[i % FIRST_NAMES.length];
    const last = LAST_NAMES[(i * 7) % LAST_NAMES.length];
    const dept = DEPARTMENTS[i % DEPARTMENTS.length];
    const year = 2015 + (i % 10);
    const month = String((i % 12) + 1).padStart(2, "0");
    const day = String((i % 28) + 1).padStart(2, "0");
    rows.push({
      id: i + 1,
      name: `${first} ${last}`,
      email: `${first.toLowerCase()}.${last.toLowerCase()}${i}@example.com`,
      age: 22 + (i % 40),
      department: dept,
      salary: 40000 + ((i * 137) % 80000),
      joinDate: `${year}-${month}-${day}`,
    });
  }
  return rows;
}

const MOCK_DATA: Row[] = generateMockData(TOTAL_ROWS);

const COLUMNS: ColumnDef[] = [
  { key: "id", title: "ID", width: 70, sortable: true, dataType: "number" },
  { key: "name", title: "Name", width: 160, sortable: true, dataType: "string" },
  { key: "email", title: "Email", width: 260, sortable: true, dataType: "string" },
  { key: "age", title: "Age", width: 70, sortable: true, dataType: "number" },
  { key: "department", title: "Department", width: 130, sortable: true, dataType: "string" },
  { key: "salary", title: "Salary", width: 110, sortable: true, dataType: "number" },
  { key: "joinDate", title: "Join Date", width: 120, sortable: true, dataType: "date" },
];

// ─── Helpers ───

function calculateVisibleRange(
  scrollTop: number,
  viewportHeight: number,
  rowHeight: number,
  totalRows: number,
  overscan: number
): VisibleRange {
  const startIndex = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan);
  const visibleCount = Math.ceil(viewportHeight / rowHeight);
  const endIndex = Math.min(totalRows - 1, startIndex + visibleCount + overscan * 2);
  const offsetY = startIndex * rowHeight;
  return { startIndex, endIndex, offsetY };
}

function toggleSort(current: SortConfig, key: string): SortConfig {
  if (current.key !== key) return { key, direction: "asc" };
  if (current.direction === "asc") return { key, direction: "desc" };
  if (current.direction === "desc") return { key: null, direction: null };
  return { key, direction: "asc" };
}

function filterRows(rows: Row[], filterText: string): Row[] {
  if (!filterText.trim()) return rows;
  const lower = filterText.toLowerCase();
  return rows.filter((row) =>
    Object.values(row).some((v) => String(v).toLowerCase().includes(lower))
  );
}

function sortRows(rows: Row[], config: SortConfig): Row[] {
  if (!config.key || !config.direction) return rows;
  const k = config.key;
  const dir = config.direction === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const av = a[k];
    const bv = b[k];
    if (typeof av === "number" && typeof bv === "number") return (av - bv) * dir;
    return String(av).localeCompare(String(bv)) * dir;
  });
}

// ─── Component ───

const VirtualGrid: React.FC = () => {
  const bodyRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [sortConfig, setSortConfig] = useState<SortConfig>({ key: null, direction: null });
  const [filterText, setFilterText] = useState("");
  const rafRef = useRef<number | null>(null);

  const filtered = useMemo(() => filterRows(MOCK_DATA, filterText), [filterText]);
  const sorted = useMemo(() => sortRows(filtered, sortConfig), [filtered, sortConfig]);
  const totalRows = sorted.length;

  const { startIndex, endIndex, offsetY } = useMemo(
    () => calculateVisibleRange(scrollTop, VIEWPORT_HEIGHT, ROW_HEIGHT, totalRows, OVERSCAN),
    [scrollTop, totalRows]
  );

  const totalHeight = totalRows * ROW_HEIGHT;
  const visibleRows = sorted.slice(startIndex, endIndex + 1);

  const handleScroll = useCallback(() => {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => {
      if (bodyRef.current) {
        setScrollTop(bodyRef.current.scrollTop);
      }
    });
  }, []);

  useEffect(() => {
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  const handleSort = useCallback(
    (key: string) => {
      setSortConfig((prev) => toggleSort(prev, key));
    },
    []
  );

  const sortIndicator = (key: string) => {
    if (sortConfig.key !== key) return " ↕";
    return sortConfig.direction === "asc" ? " ↑" : " ↓";
  };

  const handleFilterChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setFilterText(e.target.value);
  }, []);

  return (
    <div style={cls.container}>
      <div style={cls.filterRow}>
        <input
          style={cls.filterInput}
          placeholder="Search across all columns..."
          value={filterText}
          onChange={handleFilterChange}
        />
      </div>

      {/* Header */}
      <div style={cls.headerRow}>
        {COLUMNS.map((col) => (
          <div
            key={col.key}
            style={{ ...cls.headerCell, width: col.width, minWidth: col.width }}
            onClick={() => col.sortable && handleSort(col.key)}
          >
            {col.title}
            {col.sortable && <span style={{ fontSize: 11, color: "#999" }}>{sortIndicator(col.key)}</span>}
          </div>
        ))}
      </div>

      {/* Body */}
      <div
        ref={bodyRef}
        style={{ ...cls.bodyContainer, height: VIEWPORT_HEIGHT }}
        onScroll={handleScroll}
      >
        <div style={{ height: totalHeight, position: "relative" }}>
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              transform: `translateY(${offsetY}px)`,
              willChange: "transform",
            }}
          >
            {visibleRows.map((row, i) => {
              const absIdx = startIndex + i;
              return (
                <div
                  key={row.id}
                  style={{
                    ...cls.row,
                    height: ROW_HEIGHT,
                    ...(absIdx % 2 === 0 ? cls.rowEven : {}),
                  }}
                >
                  {COLUMNS.map((col) => (
                    <div
                      key={col.key}
                      style={{ ...cls.cell, width: col.width, minWidth: col.width, lineHeight: `${ROW_HEIGHT - 12}px` }}
                    >
                      {col.key === "salary"
                        ? `$${Number(row[col.key]).toLocaleString()}`
                        : String(row[col.key])}
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Footer info */}
      <div style={cls.info}>
        <span>
          Showing {startIndex + 1}-{Math.min(endIndex + 1, totalRows)} of {totalRows} rows
        </span>
        <span>{filterText ? `(filtered from ${TOTAL_ROWS})` : `${TOTAL_ROWS} total`}</span>
      </div>
    </div>
  );
};

export default VirtualGrid;
