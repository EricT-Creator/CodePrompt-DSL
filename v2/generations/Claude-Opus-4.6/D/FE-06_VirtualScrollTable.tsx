import React, { useState, useRef, useCallback, useEffect, useMemo } from "react";

type SortDirection = "asc" | "desc" | null;
interface SortConfig {
  column: keyof RowData;
  direction: SortDirection;
}

interface RowData {
  id: number;
  name: string;
  value: number;
  status: string;
}

const ROW_HEIGHT = 40;
const BUFFER_ROWS = 10;
const TOTAL_ROWS = 10000;

function generateData(): RowData[] {
  const statuses = ["Active", "Inactive", "Pending", "Archived", "Draft"];
  const names = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta", "Iota", "Kappa"];
  const data: RowData[] = [];
  for (let i = 0; i < TOTAL_ROWS; i++) {
    data.push({
      id: i + 1,
      name: `${names[i % names.length]}-${Math.floor(i / names.length) + 1}`,
      value: Math.floor(Math.random() * 10000),
      status: statuses[i % statuses.length],
    });
  }
  return data;
}

const VirtualScrollTable: React.FC = () => {
  const [rawData] = useState<RowData[]>(generateData);
  const [sortConfig, setSortConfig] = useState<SortConfig>({ column: "id", direction: null });
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const sortedData = useMemo(() => {
    if (!sortConfig.direction) return rawData;
    const sorted = [...rawData];
    sorted.sort((a, b) => {
      const aVal = a[sortConfig.column];
      const bVal = b[sortConfig.column];
      if (typeof aVal === "number" && typeof bVal === "number") {
        return sortConfig.direction === "asc" ? aVal - bVal : bVal - aVal;
      }
      const aStr = String(aVal);
      const bStr = String(bVal);
      return sortConfig.direction === "asc"
        ? aStr.localeCompare(bStr)
        : bStr.localeCompare(aStr);
    });
    return sorted;
  }, [rawData, sortConfig]);

  const containerHeight = useMemo(() => {
    if (typeof window !== "undefined") return window.innerHeight - 120;
    return 600;
  }, []);

  const visibleCount = Math.ceil(containerHeight / ROW_HEIGHT);
  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - BUFFER_ROWS);
  const endIndex = Math.min(sortedData.length, Math.floor(scrollTop / ROW_HEIGHT) + visibleCount + BUFFER_ROWS);
  const visibleRows = sortedData.slice(startIndex, endIndex);
  const totalHeight = sortedData.length * ROW_HEIGHT;
  const offsetY = startIndex * ROW_HEIGHT;

  const handleScroll = useCallback(() => {
    if (containerRef.current) {
      setScrollTop(containerRef.current.scrollTop);
    }
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (el) {
      el.addEventListener("scroll", handleScroll, { passive: true });
      return () => el.removeEventListener("scroll", handleScroll);
    }
  }, [handleScroll]);

  const handleSort = useCallback((column: keyof RowData) => {
    setSortConfig((prev) => {
      if (prev.column === column) {
        const next: SortDirection =
          prev.direction === null ? "asc" : prev.direction === "asc" ? "desc" : null;
        return { column, direction: next };
      }
      return { column, direction: "asc" };
    });
  }, []);

  const sortIndicator = (column: keyof RowData): string => {
    if (sortConfig.column !== column || !sortConfig.direction) return " ⇅";
    return sortConfig.direction === "asc" ? " ▲" : " ▼";
  };

  return (
    <div className="vst-wrapper">
      <h2 className="vst-title">Virtual Scroll Table ({TOTAL_ROWS.toLocaleString()} rows)</h2>
      <div className="vst-table-container">
        <div className="vst-header">
          <div className="vst-header-cell vst-col-id" onClick={() => handleSort("id")}>
            ID{sortIndicator("id")}
          </div>
          <div className="vst-header-cell vst-col-name" onClick={() => handleSort("name")}>
            Name{sortIndicator("name")}
          </div>
          <div className="vst-header-cell vst-col-value" onClick={() => handleSort("value")}>
            Value{sortIndicator("value")}
          </div>
        </div>
        <div
          ref={containerRef}
          className="vst-scroll-area"
          style={{ height: `${containerHeight}px` }}
        >
          <div className="vst-spacer" style={{ height: `${totalHeight}px` }}>
            <div className="vst-row-group" style={{ transform: `translateY(${offsetY}px)` }}>
              {visibleRows.map((row) => (
                <div
                  key={row.id}
                  className={`vst-row ${row.id % 2 === 0 ? "vst-row-even" : ""}`}
                  style={{ height: `${ROW_HEIGHT}px` }}
                >
                  <div className="vst-cell vst-col-id">{row.id}</div>
                  <div className="vst-cell vst-col-name">{row.name}</div>
                  <div className="vst-cell vst-col-value">{row.value.toLocaleString()}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VirtualScrollTable;

/*
=== CSS Module Content (VirtualScrollTable.module.css) ===

.vst-wrapper {
  font-family: system-ui, -apple-system, sans-serif;
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.vst-title {
  text-align: center;
  color: #333;
  margin-bottom: 16px;
  font-size: 20px;
}

.vst-table-container {
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
}

.vst-header {
  display: flex;
  background: #f5f5f5;
  border-bottom: 2px solid #ddd;
  position: sticky;
  top: 0;
  z-index: 2;
}

.vst-header-cell {
  padding: 12px 16px;
  font-weight: 600;
  color: #555;
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;
}

.vst-header-cell:hover {
  background: #e8e8e8;
}

.vst-col-id {
  width: 100px;
  flex-shrink: 0;
}

.vst-col-name {
  flex: 1;
}

.vst-col-value {
  width: 150px;
  flex-shrink: 0;
  text-align: right;
}

.vst-scroll-area {
  overflow-y: auto;
  position: relative;
}

.vst-spacer {
  position: relative;
}

.vst-row-group {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
}

.vst-row {
  display: flex;
  align-items: center;
  border-bottom: 1px solid #f0f0f0;
}

.vst-row-even {
  background: #fafafa;
}

.vst-cell {
  padding: 8px 16px;
  color: #333;
  font-size: 14px;
}

=== End CSS Module ===
*/
