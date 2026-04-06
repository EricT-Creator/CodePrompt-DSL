## Constraint Review
- C1 (TS + React): PASS — File uses TypeScript interfaces (RowData, SortConfig) and React hooks (useRef, useMemo, useState, useCallback, useEffect).
- C2 (Manual virtual scroll, no windowing libs): PASS — Virtual scroll implemented manually via `startIndex`/`endIndex` calculation from `scrollTop`, absolute positioning with `top`, and overscan buffer; no react-window or react-virtualized imported.
- C3 (CSS Modules, no Tailwind/inline): FAIL — Styles defined as inline `React.CSSProperties` objects (`const css: Record<string, React.CSSProperties>`), not CSS Modules (`.module.css` imports).
- C4 (No external deps): PASS — Only import is `from "react"`; no external dependencies.
- C5 (Single file, export default): PASS — All code in one file, ends with `export default DataGrid`.
- C6 (Inline mock data): PASS — `generateMockData()` function generates 10,000 rows inline with deterministic values.

## Functionality Assessment (0-5)
Score: 5 — Complete virtual scroll data grid with 10k rows, column sorting (multi-toggle asc/desc/none), text filter on name/email, RAF-throttled scroll handler, React.memo row optimization, overscan buffer, and accurate row count display. Well-structured and performant.

## Corrected Code
```tsx
import React, { useRef, useMemo, useReducer, useCallback, useEffect } from "react";

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

// ---- CSS Module Simulation via <style> tag ----

const CLS = "vsg_";

const cn = {
  container: `${CLS}container`,
  title: `${CLS}title`,
  filterBar: `${CLS}filterBar`,
  filterInput: `${CLS}filterInput`,
  filterLabel: `${CLS}filterLabel`,
  statsText: `${CLS}statsText`,
  gridWrapper: `${CLS}gridWrapper`,
  headerRow: `${CLS}headerRow`,
  headerCell: `${CLS}headerCell`,
  scrollContainer: `${CLS}scrollContainer`,
  row: `${CLS}row`,
  rowEven: `${CLS}rowEven`,
  rowOdd: `${CLS}rowOdd`,
  cell: `${CLS}cell`,
  sortActive: `${CLS}sortActive`,
  sortInactive: `${CLS}sortInactive`,
};

const CSS_TEXT = `
.${cn.container} {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  padding: 20px;
  max-width: 1000px;
  margin: 0 auto;
  background-color: #f5f5f5;
  min-height: 100vh;
}
.${cn.title} {
  font-size: 22px;
  font-weight: bold;
  color: #333;
  margin-bottom: 16px;
}
.${cn.filterBar} {
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.${cn.filterInput} {
  padding: 8px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 14px;
  width: 300px;
}
.${cn.filterLabel} {
  font-size: 14px;
  color: #555;
}
.${cn.statsText} {
  font-size: 12px;
  color: #999;
  margin-left: auto;
}
.${cn.gridWrapper} {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
  overflow: hidden;
}
.${cn.headerRow} {
  display: flex;
  background-color: #f8f9fa;
  border-bottom: 2px solid #dee2e6;
  position: sticky;
  top: 0;
  z-index: 10;
}
.${cn.headerCell} {
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 600;
  color: #495057;
  cursor: pointer;
  user-select: none;
  border-right: 1px solid #eee;
  display: flex;
  align-items: center;
  gap: 4px;
}
.${cn.scrollContainer} {
  overflow-y: auto;
  height: ${VIEWPORT_HEIGHT}px;
  position: relative;
}
.${cn.row} {
  display: flex;
  position: absolute;
  width: 100%;
  border-bottom: 1px solid #f0f0f0;
  will-change: transform;
}
.${cn.rowEven} { background-color: #fff; }
.${cn.rowOdd} { background-color: #fafafa; }
.${cn.cell} {
  padding: 8px 12px;
  font-size: 13px;
  color: #333;
  border-right: 1px solid #f5f5f5;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.${cn.sortActive} { color: #007bff; }
.${cn.sortInactive} { color: #bbb; }
`;

const columnWidths: Record<keyof RowData, string> = {
  id: "80px",
  name: "160px",
  email: "240px",
  age: "80px",
  city: "140px",
  score: "100px",
};

const sortableColumns: Set<keyof RowData> = new Set(["name", "score", "age", "city"]);

// ---- State Reducer ----

interface GridState {
  filter: string;
  sort: SortConfig;
  scrollTop: number;
}

type GridAction =
  | { type: "SET_FILTER"; value: string }
  | { type: "SET_SORT"; column: keyof RowData }
  | { type: "SET_SCROLL_TOP"; value: number };

function gridReducer(state: GridState, action: GridAction): GridState {
  switch (action.type) {
    case "SET_FILTER":
      return { ...state, filter: action.value };
    case "SET_SORT": {
      const col = action.column;
      if (state.sort.column !== col) return { ...state, sort: { column: col, direction: "asc" } };
      if (state.sort.direction === "asc") return { ...state, sort: { column: col, direction: "desc" } };
      return { ...state, sort: { column: null, direction: null } };
    }
    case "SET_SCROLL_TOP":
      return { ...state, scrollTop: action.value };
    default:
      return state;
  }
}

// ---- Components ----

const GridRow = React.memo<{ row: RowData; top: number; isEven: boolean }>(
  ({ row, top, isEven }) => (
    <div
      className={`${cn.row} ${isEven ? cn.rowEven : cn.rowOdd}`}
      style={{ top: `${top}px`, height: `${ROW_HEIGHT}px` }}
    >
      {(Object.keys(columnWidths) as (keyof RowData)[]).map((col) => (
        <div key={col} className={cn.cell} style={{ width: columnWidths[col], flexShrink: 0 }}>
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
  <div className={cn.filterBar}>
    <span className={cn.filterLabel}>Search:</span>
    <input
      className={cn.filterInput}
      value={filter}
      onChange={(e) => onChange(e.target.value)}
      placeholder="Filter by name or email..."
    />
    <span className={cn.statsText}>
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
    <div className={cn.headerRow}>
      {(Object.keys(columnWidths) as (keyof RowData)[]).map((col) => (
        <div
          key={col}
          className={cn.headerCell}
          style={{
            width: columnWidths[col],
            flexShrink: 0,
            cursor: sortableColumns.has(col) ? "pointer" : "default",
          }}
          onClick={() => sortableColumns.has(col) && onSort(col)}
        >
          {col.charAt(0).toUpperCase() + col.slice(1)}
          {sortableColumns.has(col) && (
            <span className={sort.column === col ? cn.sortActive : cn.sortInactive}>
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

  const [state, dispatch] = useReducer(gridReducer, {
    filter: "",
    sort: { column: null, direction: null },
    scrollTop: 0,
  });

  const filteredData = useMemo(() => {
    if (!state.filter) return rawDataRef.current;
    const lowerFilter = state.filter.toLowerCase();
    return rawDataRef.current.filter(
      (row) =>
        row.name.toLowerCase().includes(lowerFilter) ||
        row.email.toLowerCase().includes(lowerFilter)
    );
  }, [state.filter]);

  const sortedData = useMemo(() => {
    if (!state.sort.column || !state.sort.direction) return filteredData;
    const col = state.sort.column;
    const dir = state.sort.direction === "asc" ? 1 : -1;
    return [...filteredData].sort((a, b) => {
      const aVal = a[col];
      const bVal = b[col];
      if (typeof aVal === "string" && typeof bVal === "string") {
        return aVal.localeCompare(bVal) * dir;
      }
      return ((aVal as number) - (bVal as number)) * dir;
    });
  }, [filteredData, state.sort]);

  const totalRows = sortedData.length;
  const totalHeight = totalRows * ROW_HEIGHT;

  const startIndex = Math.max(0, Math.floor(state.scrollTop / ROW_HEIGHT) - OVERSCAN);
  const endIndex = Math.min(totalRows - 1, Math.ceil((state.scrollTop + VIEWPORT_HEIGHT) / ROW_HEIGHT) + OVERSCAN);

  const visibleRows = sortedData.slice(startIndex, endIndex + 1);

  const handleScroll = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => {
      if (scrollRef.current) {
        dispatch({ type: "SET_SCROLL_TOP", value: scrollRef.current.scrollTop });
      }
    });
  }, []);

  useEffect(() => {
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  const handleSort = useCallback((col: keyof RowData) => {
    dispatch({ type: "SET_SORT", column: col });
  }, []);

  const handleFilterChange = useCallback((value: string) => {
    dispatch({ type: "SET_FILTER", value });
  }, []);

  return (
    <div className={cn.container}>
      <style>{CSS_TEXT}</style>
      <div className={cn.title}>Virtual Scroll Data Grid</div>
      <FilterBar
        filter={state.filter}
        onChange={handleFilterChange}
        totalRows={TOTAL_ROWS}
        filteredCount={totalRows}
      />
      <div className={cn.gridWrapper}>
        <GridHeader sort={state.sort} onSort={handleSort} />
        <div
          ref={scrollRef}
          className={cn.scrollContainer}
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
```
