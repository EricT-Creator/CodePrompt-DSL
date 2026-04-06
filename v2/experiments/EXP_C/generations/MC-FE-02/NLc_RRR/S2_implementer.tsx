import React, { useRef, useMemo, useState, useCallback, useEffect } from "react";

// ---- Types ----

interface RowData {
  id: number;
  name: string;
  email: string;
  age: number;
  city: string;
  score: number;
}

interface SortConfig {
  column: keyof RowData | null;
  direction: "asc" | "desc" | null;
}

// ---- Constants ----

const ROW_HEIGHT = 36;
const VIEWPORT_HEIGHT = 600;
const OVERSCAN = 5;
const TOTAL_ROWS = 10000;

const CITIES = ["New York", "London", "Tokyo", "Paris", "Berlin", "Sydney", "Toronto", "Mumbai", "Seoul", "Shanghai"];
const DOMAINS = ["example.com", "test.org", "demo.net", "mail.io", "corp.dev"];

// ---- Inline Mock Data ----

function generateMockData(): RowData[] {
  const data: RowData[] = [];
  for (let i = 0; i < TOTAL_ROWS; i++) {
    data.push({
      id: i,
      name: `User ${i}`,
      email: `user${i}@${DOMAINS[i % DOMAINS.length]}`,
      age: 18 + (i % 60),
      city: CITIES[i % CITIES.length],
      score: Math.round(((i * 7 + 13) % 1000) / 10),
    });
  }
  return data;
}

// ---- Styles (CSS Module simulation) ----

const css: Record<string, React.CSSProperties> = {
  container: {
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    padding: "20px",
    maxWidth: "1000px",
    margin: "0 auto",
    backgroundColor: "#f5f5f5",
    minHeight: "100vh",
  },
  title: {
    fontSize: "22px",
    fontWeight: "bold",
    color: "#333",
    marginBottom: "16px",
  },
  filterBar: {
    marginBottom: "12px",
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  filterInput: {
    padding: "8px 12px",
    border: "1px solid #ccc",
    borderRadius: "4px",
    fontSize: "14px",
    width: "300px",
  },
  filterLabel: {
    fontSize: "14px",
    color: "#555",
  },
  statsText: {
    fontSize: "12px",
    color: "#999",
    marginLeft: "auto",
  },
  gridWrapper: {
    backgroundColor: "#fff",
    borderRadius: "8px",
    boxShadow: "0 1px 4px rgba(0,0,0,0.1)",
    overflow: "hidden",
  },
  headerRow: {
    display: "flex",
    backgroundColor: "#f8f9fa",
    borderBottom: "2px solid #dee2e6",
    position: "sticky" as const,
    top: 0,
    zIndex: 10,
  },
  headerCell: {
    padding: "10px 12px",
    fontSize: "13px",
    fontWeight: "600",
    color: "#495057",
    cursor: "pointer",
    userSelect: "none" as const,
    borderRight: "1px solid #eee",
    display: "flex",
    alignItems: "center",
    gap: "4px",
  },
  scrollContainer: {
    overflowY: "auto" as const,
    height: `${VIEWPORT_HEIGHT}px`,
    position: "relative" as const,
  },
  row: {
    display: "flex",
    position: "absolute" as const,
    width: "100%",
    borderBottom: "1px solid #f0f0f0",
    willChange: "transform",
  },
  cell: {
    padding: "8px 12px",
    fontSize: "13px",
    color: "#333",
    borderRight: "1px solid #f5f5f5",
    overflow: "hidden" as const,
    textOverflow: "ellipsis" as const,
    whiteSpace: "nowrap" as const,
  },
};

const columnWidths: Record<keyof RowData, string> = {
  id: "80px",
  name: "160px",
  email: "240px",
  age: "80px",
  city: "140px",
  score: "100px",
};

const sortableColumns: Set<keyof RowData> = new Set(["name", "score", "age", "city"]);

// ---- Components ----

const GridRow = React.memo<{ row: RowData; top: number; isEven: boolean }>(
  ({ row, top, isEven }) => (
    <div
      style={{
        ...css.row,
        top: `${top}px`,
        height: `${ROW_HEIGHT}px`,
        backgroundColor: isEven ? "#fff" : "#fafafa",
      }}
    >
      {(Object.keys(columnWidths) as (keyof RowData)[]).map((col) => (
        <div key={col} style={{ ...css.cell, width: columnWidths[col], flexShrink: 0 }}>
          {row[col]}
        </div>
      ))}
    </div>
  )
);

const FilterBar: React.FC<{
  filter: string;
  onChange: (v: string) => void;
  totalRows: number;
  filteredCount: number;
}> = ({ filter, onChange, totalRows, filteredCount }) => (
  <div style={css.filterBar}>
    <span style={css.filterLabel}>Search:</span>
    <input
      style={css.filterInput}
      value={filter}
      onChange={(e) => onChange(e.target.value)}
      placeholder="Filter by name or email..."
    />
    <span style={css.statsText}>
      Showing {filteredCount.toLocaleString()} of {totalRows.toLocaleString()} rows
    </span>
  </div>
);

const GridHeader: React.FC<{
  sort: SortConfig;
  onSort: (col: keyof RowData) => void;
}> = ({ sort, onSort }) => {
  const getSortIndicator = (col: keyof RowData): string => {
    if (sort.column !== col || !sort.direction) return "";
    return sort.direction === "asc" ? " ↑" : " ↓";
  };

  return (
    <div style={css.headerRow}>
      {(Object.keys(columnWidths) as (keyof RowData)[]).map((col) => (
        <div
          key={col}
          style={{
            ...css.headerCell,
            width: columnWidths[col],
            flexShrink: 0,
            cursor: sortableColumns.has(col) ? "pointer" : "default",
          }}
          onClick={() => sortableColumns.has(col) && onSort(col)}
        >
          {col.charAt(0).toUpperCase() + col.slice(1)}
          {sortableColumns.has(col) && (
            <span style={{ color: sort.column === col ? "#007bff" : "#bbb" }}>
              {getSortIndicator(col) || " ⇅"}
            </span>
          )}
        </div>
      ))}
    </div>
  );
};

// ---- Main Component ----

const DataGrid: React.FC = () => {
  const rawDataRef = useRef<RowData[]>(generateMockData());
  const scrollRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number>(0);

  const [filter, setFilter] = useState("");
  const [sort, setSort] = useState<SortConfig>({ column: null, direction: null });
  const [scrollTop, setScrollTop] = useState(0);

  const filteredData = useMemo(() => {
    if (!filter) return rawDataRef.current;
    const lowerFilter = filter.toLowerCase();
    return rawDataRef.current.filter(
      (row) =>
        row.name.toLowerCase().includes(lowerFilter) ||
        row.email.toLowerCase().includes(lowerFilter)
    );
  }, [filter]);

  const sortedData = useMemo(() => {
    if (!sort.column || !sort.direction) return filteredData;
    const col = sort.column;
    const dir = sort.direction === "asc" ? 1 : -1;
    return [...filteredData].sort((a, b) => {
      const aVal = a[col];
      const bVal = b[col];
      if (typeof aVal === "string" && typeof bVal === "string") {
        return aVal.localeCompare(bVal) * dir;
      }
      return ((aVal as number) - (bVal as number)) * dir;
    });
  }, [filteredData, sort]);

  const totalRows = sortedData.length;
  const totalHeight = totalRows * ROW_HEIGHT;

  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const endIndex = Math.min(totalRows - 1, Math.ceil((scrollTop + VIEWPORT_HEIGHT) / ROW_HEIGHT) + OVERSCAN);

  const visibleRows = sortedData.slice(startIndex, endIndex + 1);

  const handleScroll = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => {
      if (scrollRef.current) {
        setScrollTop(scrollRef.current.scrollTop);
      }
    });
  }, []);

  useEffect(() => {
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  const handleSort = useCallback((col: keyof RowData) => {
    setSort((prev) => {
      if (prev.column !== col) return { column: col, direction: "asc" };
      if (prev.direction === "asc") return { column: col, direction: "desc" };
      return { column: null, direction: null };
    });
  }, []);

  return (
    <div style={css.container}>
      <div style={css.title}>Virtual Scroll Data Grid</div>
      <FilterBar
        filter={filter}
        onChange={setFilter}
        totalRows={TOTAL_ROWS}
        filteredCount={totalRows}
      />
      <div style={css.gridWrapper}>
        <GridHeader sort={sort} onSort={handleSort} />
        <div
          ref={scrollRef}
          style={css.scrollContainer}
          onScroll={handleScroll}
        >
          <div style={{ height: `${totalHeight}px`, position: "relative" }}>
            {visibleRows.map((row, i) => {
              const actualIndex = startIndex + i;
              return (
                <GridRow
                  key={row.id}
                  row={row}
                  top={actualIndex * ROW_HEIGHT}
                  isEven={actualIndex % 2 === 0}
                />
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DataGrid;
