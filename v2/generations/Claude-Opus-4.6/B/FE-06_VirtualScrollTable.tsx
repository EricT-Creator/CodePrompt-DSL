import React, { useState, useRef, useCallback, useEffect, useMemo } from "react";

/*
=== CSS Module Content (VirtualScrollTable.module.css) ===

.container {
  max-width: 800px;
  margin: 40px auto;
  font-family: system-ui, -apple-system, sans-serif;
  border: 1px solid #d0d0d0;
  border-radius: 8px;
  overflow: hidden;
}

.headerRow {
  display: flex;
  background-color: #1a1a2e;
  color: #ffffff;
  font-weight: 600;
  position: sticky;
  top: 0;
  z-index: 2;
}

.headerCell {
  flex: 1;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
  display: flex;
  align-items: center;
  gap: 6px;
  border-right: 1px solid rgba(255,255,255,0.1);
  transition: background-color 0.15s;
}

.headerCell:hover {
  background-color: rgba(255,255,255,0.1);
}

.headerCell:last-child {
  border-right: none;
}

.scrollContainer {
  height: 500px;
  overflow-y: auto;
  position: relative;
}

.row {
  display: flex;
  border-bottom: 1px solid #eee;
}

.row:hover {
  background-color: #f5f8ff;
}

.rowEven {
  background-color: #fafafa;
}

.cell {
  flex: 1;
  padding: 10px 16px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sortArrow {
  font-size: 12px;
  opacity: 0.8;
}

.info {
  padding: 8px 16px;
  background: #f0f0f0;
  font-size: 13px;
  color: #666;
  text-align: center;
}

=== End CSS Module Content ===
*/

type SortDirection = "asc" | "desc" | null;

interface SortConfig {
  column: string;
  direction: SortDirection;
}

interface RowData {
  id: number;
  name: string;
  value: number;
  category: string;
}

const ROW_HEIGHT = 41;
const OVERSCAN = 5;
const TOTAL_ROWS = 10000;

const categories = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta"];

function generateData(count: number): RowData[] {
  const data: RowData[] = [];
  for (let i = 0; i < count; i++) {
    data.push({
      id: i + 1,
      name: `Item ${String(i + 1).padStart(5, "0")}`,
      value: Math.round(Math.random() * 10000) / 100,
      category: categories[i % categories.length],
    });
  }
  return data;
}

const cssModule: Record<string, string> = {
  container: "vsTable_container",
  headerRow: "vsTable_headerRow",
  headerCell: "vsTable_headerCell",
  scrollContainer: "vsTable_scrollContainer",
  row: "vsTable_row",
  rowEven: "vsTable_rowEven",
  cell: "vsTable_cell",
  sortArrow: "vsTable_sortArrow",
  info: "vsTable_info",
};

const injectStyles = (): void => {
  const id = "vsTable_injected_styles";
  if (document.getElementById(id)) return;
  const style = document.createElement("style");
  style.id = id;
  style.textContent = `
    .${cssModule.container} {
      max-width: 800px;
      margin: 40px auto;
      font-family: system-ui, -apple-system, sans-serif;
      border: 1px solid #d0d0d0;
      border-radius: 8px;
      overflow: hidden;
    }
    .${cssModule.headerRow} {
      display: flex;
      background-color: #1a1a2e;
      color: #ffffff;
      font-weight: 600;
    }
    .${cssModule.headerCell} {
      flex: 1;
      padding: 12px 16px;
      cursor: pointer;
      user-select: none;
      display: flex;
      align-items: center;
      gap: 6px;
      border-right: 1px solid rgba(255,255,255,0.1);
      transition: background-color 0.15s;
    }
    .${cssModule.headerCell}:hover {
      background-color: rgba(255,255,255,0.1);
    }
    .${cssModule.headerCell}:last-child {
      border-right: none;
    }
    .${cssModule.scrollContainer} {
      height: 500px;
      overflow-y: auto;
      position: relative;
    }
    .${cssModule.row} {
      display: flex;
      border-bottom: 1px solid #eee;
    }
    .${cssModule.row}:hover {
      background-color: #f5f8ff;
    }
    .${cssModule.rowEven} {
      background-color: #fafafa;
    }
    .${cssModule.cell} {
      flex: 1;
      padding: 10px 16px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .${cssModule.sortArrow} {
      font-size: 12px;
      opacity: 0.8;
    }
    .${cssModule.info} {
      padding: 8px 16px;
      background: #f0f0f0;
      font-size: 13px;
      color: #666;
      text-align: center;
    }
  `;
  document.head.appendChild(style);
};

const columns: { key: keyof RowData; label: string }[] = [
  { key: "id", label: "ID" },
  { key: "name", label: "Name" },
  { key: "value", label: "Value" },
];

export default function VirtualScrollTable() {
  const [rawData] = useState<RowData[]>(() => generateData(TOTAL_ROWS));
  const [sortConfig, setSortConfig] = useState<SortConfig>({ column: "", direction: null });
  const [scrollTop, setScrollTop] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    injectStyles();
  }, []);

  const sortedData = useMemo(() => {
    if (!sortConfig.column || !sortConfig.direction) return rawData;
    const col = sortConfig.column as keyof RowData;
    const dir = sortConfig.direction === "asc" ? 1 : -1;
    return [...rawData].sort((a, b) => {
      const av = a[col];
      const bv = b[col];
      if (typeof av === "number" && typeof bv === "number") {
        return (av - bv) * dir;
      }
      return String(av).localeCompare(String(bv)) * dir;
    });
  }, [rawData, sortConfig]);

  const handleSort = (colKey: string) => {
    setSortConfig((prev) => {
      if (prev.column === colKey) {
        if (prev.direction === "asc") return { column: colKey, direction: "desc" };
        if (prev.direction === "desc") return { column: "", direction: null };
      }
      return { column: colKey, direction: "asc" };
    });
  };

  const handleScroll = useCallback(() => {
    if (scrollRef.current) {
      setScrollTop(scrollRef.current.scrollTop);
    }
  }, []);

  const totalHeight = sortedData.length * ROW_HEIGHT;
  const containerHeight = 500;
  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const endIndex = Math.min(
    sortedData.length,
    Math.ceil((scrollTop + containerHeight) / ROW_HEIGHT) + OVERSCAN
  );
  const visibleRows = sortedData.slice(startIndex, endIndex);
  const offsetY = startIndex * ROW_HEIGHT;

  const getSortArrow = (colKey: string): string => {
    if (sortConfig.column !== colKey) return "";
    return sortConfig.direction === "asc" ? "▲" : "▼";
  };

  return (
    <div className={cssModule.container}>
      <div className={cssModule.headerRow}>
        {columns.map((col) => (
          <div
            key={col.key}
            className={cssModule.headerCell}
            onClick={() => handleSort(col.key)}
          >
            <span>{col.label}</span>
            {getSortArrow(col.key) && (
              <span className={cssModule.sortArrow}>{getSortArrow(col.key)}</span>
            )}
          </div>
        ))}
      </div>
      <div
        ref={scrollRef}
        className={cssModule.scrollContainer}
        onScroll={handleScroll}
      >
        <div style={{ height: totalHeight, position: "relative" }}>
          <div style={{ transform: `translateY(${offsetY}px)` }}>
            {visibleRows.map((row, i) => {
              const actualIndex = startIndex + i;
              return (
                <div
                  key={row.id}
                  className={`${cssModule.row} ${actualIndex % 2 === 0 ? cssModule.rowEven : ""}`}
                  style={{ height: ROW_HEIGHT }}
                >
                  <div className={cssModule.cell}>{row.id}</div>
                  <div className={cssModule.cell}>{row.name}</div>
                  <div className={cssModule.cell}>{row.value.toFixed(2)}</div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
      <div className={cssModule.info}>
        Showing rows {startIndex + 1}–{endIndex} of {sortedData.length} | Rendered: {visibleRows.length}
      </div>
    </div>
  );
}
