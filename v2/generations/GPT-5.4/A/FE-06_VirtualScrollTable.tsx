import React, { useEffect, useMemo, useRef, useState } from "react";
import styles from "./VirtualScrollTable.module.css";

type SortKey = "id" | "name" | "price" | "stock";
type SortDirection = "asc" | "desc";

type Row = {
  id: number;
  name: string;
  price: number;
  stock: number;
};

const ROW_HEIGHT = 48;
const VIEWPORT_HEIGHT = 432;
const OVERSCAN = 8;
const TOTAL_ROWS = 10000;

function compareValues(a: string | number, b: string | number, direction: SortDirection): number {
  if (a === b) {
    return 0;
  }

  const result = a > b ? 1 : -1;
  return direction === "asc" ? result : -result;
}

export default function VirtualScrollTable(): JSX.Element {
  const bodyRef = useRef<HTMLDivElement | null>(null);
  const topSpacerRef = useRef<HTMLTableRowElement | null>(null);
  const bottomSpacerRef = useRef<HTMLTableRowElement | null>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [sortKey, setSortKey] = useState<SortKey>("id");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");

  const rows = useMemo<Row[]>(() => {
    return Array.from({ length: TOTAL_ROWS }, (_, index) => ({
      id: index + 1,
      name: `Product ${String(index + 1).padStart(5, "0")}`,
      price: Number((((index * 17) % 5000) / 10 + 19.99).toFixed(2)),
      stock: (index * 13) % 240,
    }));
  }, []);

  const sortedRows = useMemo(() => {
    const nextRows = rows.slice();
    nextRows.sort((left, right) => compareValues(left[sortKey], right[sortKey], sortDirection));
    return nextRows;
  }, [rows, sortDirection, sortKey]);

  const visibleCount = Math.ceil(VIEWPORT_HEIGHT / ROW_HEIGHT) + OVERSCAN * 2;
  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const endIndex = Math.min(sortedRows.length, startIndex + visibleCount);
  const visibleRows = sortedRows.slice(startIndex, endIndex);
  const topHeight = startIndex * ROW_HEIGHT;
  const bottomHeight = Math.max(0, (sortedRows.length - endIndex) * ROW_HEIGHT);

  useEffect(() => {
    if (topSpacerRef.current) {
      topSpacerRef.current.style.height = `${topHeight}px`;
    }
    if (bottomSpacerRef.current) {
      bottomSpacerRef.current.style.height = `${bottomHeight}px`;
    }
  }, [bottomHeight, topHeight]);

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }

    setSortKey(key);
    setSortDirection("asc");
  };

  const renderSortLabel = (key: SortKey, label: string) => {
    const isActive = key === sortKey;
    const arrow = !isActive ? "↕" : sortDirection === "asc" ? "↑" : "↓";

    return (
      <button
        type="button"
        className={`${styles.sortButton} ${isActive ? styles.sortButtonActive : ""}`.trim()}
        onClick={() => handleSort(key)}
      >
        <span>{label}</span>
        <span className={styles.sortArrow}>{arrow}</span>
      </button>
    );
  };

  return (
    <div className={styles.container}>
      <div className={styles.headerBlock}>
        <div className={styles.metaRow}>
          <div>
            <h1 className={styles.title}>Virtual Inventory Table</h1>
            <p className={styles.subtitle}>Fixed header, sortable columns, and windowed rendering for 10,000 rows.</p>
          </div>
          <div className={styles.badge}>Rows: {TOTAL_ROWS.toLocaleString()}</div>
        </div>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>{renderSortLabel("id", "ID")}</th>
              <th>{renderSortLabel("name", "Name")}</th>
              <th>{renderSortLabel("price", "Price")}</th>
              <th>{renderSortLabel("stock", "Stock")}</th>
            </tr>
          </thead>
        </table>
      </div>

      <div
        ref={bodyRef}
        className={styles.bodyViewport}
        onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
      >
        <table className={styles.table}>
          <tbody>
            <tr ref={topSpacerRef} aria-hidden="true" className={styles.spacerRow}>
              <td colSpan={4} className={styles.spacerCell} />
            </tr>
            {visibleRows.map((row) => (
              <tr key={row.id} className={styles.dataRow}>
                <td>{row.id}</td>
                <td>{row.name}</td>
                <td>${row.price.toFixed(2)}</td>
                <td>{row.stock}</td>
              </tr>
            ))}
            <tr ref={bottomSpacerRef} aria-hidden="true" className={styles.spacerRow}>
              <td colSpan={4} className={styles.spacerCell} />
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* VirtualScrollTable.module.css
.container {
  min-height: 100%;
  background: linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%);
  padding: 24px;
  font-family: Arial, Helvetica, sans-serif;
  color: #0f172a;
}

.headerBlock {
  max-width: 920px;
  margin: 0 auto;
  background: #0f172a;
  color: #ffffff;
  border-radius: 18px 18px 0 0;
  padding: 20px 20px 12px;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.18);
}

.metaRow {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 14px;
}

.title {
  margin: 0 0 6px;
  font-size: 28px;
}

.subtitle {
  margin: 0;
  color: rgba(255, 255, 255, 0.75);
}

.badge {
  border: 1px solid rgba(148, 163, 184, 0.4);
  border-radius: 999px;
  padding: 8px 14px;
  font-weight: 700;
  background: rgba(15, 23, 42, 0.35);
}

.bodyViewport {
  max-width: 920px;
  height: 432px;
  overflow-y: auto;
  margin: 0 auto;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-top: none;
  border-radius: 0 0 18px 18px;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
}

.table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.table th,
.table td {
  text-align: left;
  padding: 14px 16px;
  border-bottom: 1px solid #e2e8f0;
  box-sizing: border-box;
}

.table th {
  font-size: 14px;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.sortButton {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  border: none;
  background: transparent;
  color: inherit;
  font: inherit;
  font-weight: 700;
  padding: 0;
  cursor: pointer;
}

.sortButtonActive {
  color: #93c5fd;
}

.sortArrow {
  color: #cbd5e1;
}

.dataRow:nth-child(even) {
  background: #f8fafc;
}

.dataRow:hover {
  background: #eff6ff;
}

.spacerRow {
  height: 0;
}

.spacerCell {
  padding: 0 !important;
  border-bottom: none !important;
}

@media (max-width: 720px) {
  .container {
    padding: 16px;
  }

  .metaRow {
    flex-direction: column;
  }
}
*/
