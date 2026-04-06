import React, { useRef, useMemo, useCallback, useState, memo } from "react";

// ─── Types ───────────────────────────────────────────────────────────────────

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

// ─── Constants ───────────────────────────────────────────────────────────────

const ROW_HEIGHT = 36;
const VIEWPORT_HEIGHT = 600;
const OVERSCAN = 5;
const TOTAL_ROWS = 10000;

const CITIES = ["New York", "London", "Tokyo", "Paris", "Berlin", "Sydney", "Toronto", "Mumbai", "Shanghai", "Seoul"];
const DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "company.org", "example.net"];

// ─── Styles (CSS Modules emulation) ──────────────────────────────────────────

const styles = `
.gridContainer { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 16px; background: #f8fafc; min-height: 100vh; }
.filterBar { margin-bottom: 12px; }
.filterInput { width: 320px; padding: 8px 14px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 14px; outline: none; transition: border-color 0.15s; }
.filterInput:focus { border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.15); }
.gridWrapper { border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden; background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.headerRow { display: flex; background: #f1f5f9; border-bottom: 2px solid #e2e8f0; position: sticky; top: 0; z-index: 2; }
.headerCell { flex: 1; padding: 10px 14px; font-size: 13px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.4px; cursor: pointer; user-select: none; display: flex; align-items: center; gap: 4px; transition: background 0.1s; }
.headerCell:hover { background: #e2e8f0; }
.sortArrow { font-size: 11px; }
.scrollContainer { height: ${VIEWPORT_HEIGHT}px; overflow-y: auto; position: relative; will-change: transform; }
.spacer { position: relative; width: 100%; }
.row { display: flex; position: absolute; width: 100%; left: 0; border-bottom: 1px solid #f1f5f9; transition: background 0.08s; }
.row:hover { background: #f8fafc; }
.rowEven { background: #fff; }
.rowOdd { background: #fafbfc; }
.cell { flex: 1; padding: 8px 14px; font-size: 13px; color: #334155; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.info { padding: 8px 16px; font-size: 12px; color: #94a3b8; display: flex; justify-content: space-between; border-top: 1px solid #f1f5f9; }
`;

// ─── Data Generator ──────────────────────────────────────────────────────────

function generateData(count: number): RowData[] {
  const data: RowData[] = [];
  for (let i = 0; i < count; i++) {
    const firstName = `User`;
    const name = `${firstName}_${i}`;
    data.push({
      id: i,
      name,
      email: `user${i}@${DOMAINS[i % DOMAINS.length]}`,
      age: 18 + (i % 60),
      city: CITIES[i % CITIES.length],
      score: Math.round(((i * 7 + 13) % 1000) / 10) / 10,
    });
  }
  return data;
}

// ─── GridRow ─────────────────────────────────────────────────────────────────

const GridRow = memo(function GridRow({
  row,
  top,
  even,
}: {
  row: RowData;
  top: number;
  even: boolean;
}) {
  return (
    <div className={`row ${even ? "rowEven" : "rowOdd"}`} style={{ top }}>
      <div className="cell">{row.id}</div>
      <div className="cell">{row.name}</div>
      <div className="cell">{row.email}</div>
      <div className="cell">{row.age}</div>
      <div className="cell">{row.city}</div>
      <div className="cell">{row.score}</div>
    </div>
  );
});

// ─── DataGrid ────────────────────────────────────────────────────────────────

function DataGrid() {
  const rawData = useRef<RowData[]>(generateData(TOTAL_ROWS));
  const scrollRef = useRef<HTMLDivElement>(null);

  const [filter, setFilter] = useState("");
  const [sort, setSort] = useState<SortConfig>({ column: null, direction: null });
  const [scrollTop, setScrollTop] = useState(0);

  const filteredData = useMemo(() => {
    if (!filter) return rawData.current;
    const lower = filter.toLowerCase();
    return rawData.current.filter(
      (r) =>
        r.name.toLowerCase().includes(lower) ||
        r.email.toLowerCase().includes(lower)
    );
  }, [filter]);

  const sortedData = useMemo(() => {
    if (!sort.column || !sort.direction) return filteredData;
    const col = sort.column;
    const dir = sort.direction === "asc" ? 1 : -1;
    return [...filteredData].sort((a, b) => {
      const va = a[col];
      const vb = b[col];
      if (typeof va === "string" && typeof vb === "string") {
        return va.localeCompare(vb) * dir;
      }
      return ((va as number) - (vb as number)) * dir;
    });
  }, [filteredData, sort]);

  const totalRows = sortedData.length;
  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const endIndex = Math.min(totalRows - 1, Math.ceil((scrollTop + VIEWPORT_HEIGHT) / ROW_HEIGHT) + OVERSCAN);
  const visibleSlice = sortedData.slice(startIndex, endIndex + 1);

  const handleScroll = useCallback(() => {
    if (scrollRef.current) {
      setScrollTop(scrollRef.current.scrollTop);
    }
  }, []);

  const handleSort = useCallback((column: keyof RowData) => {
    setSort((prev) => {
      if (prev.column === column) {
        if (prev.direction === "asc") return { column, direction: "desc" };
        if (prev.direction === "desc") return { column: null, direction: null };
      }
      return { column, direction: "asc" };
    });
  }, []);

  const sortArrow = (col: keyof RowData) => {
    if (sort.column !== col) return "";
    return sort.direction === "asc" ? " ▲" : " ▼";
  };

  const columns: { key: keyof RowData; label: string }[] = [
    { key: "id", label: "ID" },
    { key: "name", label: "Name" },
    { key: "email", label: "Email" },
    { key: "age", label: "Age" },
    { key: "city", label: "City" },
    { key: "score", label: "Score" },
  ];

  return (
    <div className="gridContainer">
      <style>{styles}</style>
      <div className="filterBar">
        <input
          className="filterInput"
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Search by name or email..."
        />
      </div>
      <div className="gridWrapper">
        <div className="headerRow">
          {columns.map((c) => (
            <div key={c.key} className="headerCell" onClick={() => handleSort(c.key)}>
              {c.label}
              <span className="sortArrow">{sortArrow(c.key)}</span>
            </div>
          ))}
        </div>
        <div className="scrollContainer" ref={scrollRef} onScroll={handleScroll}>
          <div className="spacer" style={{ height: totalRows * ROW_HEIGHT }}>
            {visibleSlice.map((row, i) => {
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
        <div className="info">
          <span>Showing {totalRows.toLocaleString()} rows</span>
          <span>
            Visible: {startIndex}–{Math.min(endIndex, totalRows - 1)}
          </span>
        </div>
      </div>
    </div>
  );
}

export default DataGrid;
