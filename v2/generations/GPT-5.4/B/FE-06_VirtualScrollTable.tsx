import React, { useMemo, useState } from "react";

type SortKey = "id" | "name" | "score";

type SortState = {
  key: SortKey;
  direction: "asc" | "desc";
};

type RowData = {
  id: number;
  name: string;
  score: number;
};

const ROW_HEIGHT = 44;
const VIEWPORT_HEIGHT = 440;
const OVERSCAN = 6;

const styles = {
  page: "VirtualScrollTable_page__a1",
  shell: "VirtualScrollTable_shell__a1",
  header: "VirtualScrollTable_header__a1",
  title: "VirtualScrollTable_title__a1",
  subtitle: "VirtualScrollTable_subtitle__a1",
  sortMeta: "VirtualScrollTable_sortMeta__a1",
  headerTable: "VirtualScrollTable_headerTable__a1",
  bodyTable: "VirtualScrollTable_bodyTable__a1",
  scrollBody: "VirtualScrollTable_scrollBody__a1",
  th: "VirtualScrollTable_th__a1",
  thButton: "VirtualScrollTable_thButton__a1",
  td: "VirtualScrollTable_td__a1",
  row: "VirtualScrollTable_row__a1",
  rowEven: "VirtualScrollTable_rowEven__a1",
  spacerCell: "VirtualScrollTable_spacerCell__a1",
  topSpacer: "VirtualScrollTable_topSpacer__a1",
  bottomSpacer: "VirtualScrollTable_bottomSpacer__a1",
  footer: "VirtualScrollTable_footer__a1",
} as const;

const css = `
.${styles.page} {
  min-height: 100vh;
  box-sizing: border-box;
  padding: 28px 16px;
  background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
  font-family: Arial, Helvetica, sans-serif;
  color: #0f172a;
}

.${styles.shell} {
  max-width: 980px;
  margin: 0 auto;
  background: #ffffff;
  border: 1px solid #dbeafe;
  border-radius: 20px;
  box-shadow: 0 22px 48px rgba(15, 23, 42, 0.08);
  overflow: hidden;
}

.${styles.header} {
  padding: 24px 24px 18px;
  border-bottom: 1px solid #e2e8f0;
}

.${styles.title} {
  margin: 0 0 8px;
  font-size: 28px;
}

.${styles.subtitle} {
  margin: 0;
  font-size: 14px;
  color: #475569;
  line-height: 1.6;
}

.${styles.sortMeta} {
  margin-top: 12px;
  display: inline-flex;
  gap: 8px;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 700;
}

.${styles.headerTable},
.${styles.bodyTable} {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.${styles.scrollBody} {
  overflow-y: auto;
  overflow-x: hidden;
}

.${styles.th} {
  background: #f8fafc;
  border-bottom: 1px solid #cbd5e1;
  padding: 0;
  text-align: left;
}

.${styles.thButton} {
  width: 100%;
  border: none;
  background: transparent;
  padding: 14px 18px;
  text-align: left;
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
  cursor: pointer;
}

.${styles.thButton}:hover {
  background: #eff6ff;
}

.${styles.td} {
  padding: 0 18px;
  border-bottom: 1px solid #e2e8f0;
  font-size: 14px;
  height: ${ROW_HEIGHT}px;
  box-sizing: border-box;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.${styles.row} {
  background: #ffffff;
}

.${styles.rowEven} {
  background: #f8fafc;
}

.${styles.spacerCell} {
  padding: 0;
  border: none;
  background: transparent;
}

.${styles.footer} {
  padding: 16px 24px 22px;
  font-size: 13px;
  color: #475569;
  line-height: 1.6;
  border-top: 1px solid #e2e8f0;
}

@media (max-width: 768px) {
  .${styles.header} {
    padding: 20px 18px 16px;
  }

  .${styles.title} {
    font-size: 24px;
  }

  .${styles.thButton},
  .${styles.td} {
    padding-left: 12px;
    padding-right: 12px;
  }

  .${styles.footer} {
    padding: 16px 18px 20px;
  }
}
`;

function buildRows(): RowData[] {
  return Array.from({ length: 10000 }, (_, index) => ({
    id: index + 1,
    name: `User ${String(index + 1).padStart(5, "0")}`,
    score: (index * 37 + 19) % 1000,
  }));
}

function sortRows(rows: RowData[], sort: SortState) {
  const multiplier = sort.direction === "asc" ? 1 : -1;
  return rows.slice().sort((left, right) => {
    const leftValue = left[sort.key];
    const rightValue = right[sort.key];

    if (leftValue < rightValue) {
      return -1 * multiplier;
    }
    if (leftValue > rightValue) {
      return 1 * multiplier;
    }
    return 0;
  });
}

export default function VirtualScrollTable() {
  const [scrollTop, setScrollTop] = useState(0);
  const [sort, setSort] = useState<SortState>({ key: "id", direction: "asc" });

  const rows = useMemo(() => buildRows(), []);
  const sortedRows = useMemo(() => sortRows(rows, sort), [rows, sort]);

  const visibleCount = Math.ceil(VIEWPORT_HEIGHT / ROW_HEIGHT);
  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const endIndex = Math.min(sortedRows.length, startIndex + visibleCount + OVERSCAN * 2);
  const visibleRows = sortedRows.slice(startIndex, endIndex);
  const topPadding = startIndex * ROW_HEIGHT;
  const bottomPadding = (sortedRows.length - endIndex) * ROW_HEIGHT;

  const dynamicCss = `
    .${styles.scrollBody} { height: ${VIEWPORT_HEIGHT}px; }
    .${styles.topSpacer} { height: ${topPadding}px; }
    .${styles.bottomSpacer} { height: ${bottomPadding}px; }
  `;

  const toggleSort = (key: SortKey) => {
    setSort((current) => {
      if (current.key === key) {
        return { key, direction: current.direction === "asc" ? "desc" : "asc" };
      }
      return { key, direction: "asc" };
    });
  };

  const getIndicator = (key: SortKey) => {
    if (sort.key !== key) {
      return "↕";
    }
    return sort.direction === "asc" ? "↑" : "↓";
  };

  return (
    <div className={styles.page}>
      <style>{css + dynamicCss}</style>
      <div className={styles.shell}>
        <div className={styles.header}>
          <h1 className={styles.title}>Virtual Scroll Table</h1>
          <p className={styles.subtitle}>
            Fixed header, three sortable columns, overscan buffer, and only the visible rows are
            rendered from a 10,000-row dataset.
          </p>
          <div className={styles.sortMeta}>
            Showing rows {startIndex + 1} - {endIndex} of {sortedRows.length}
          </div>
        </div>

        <table className={styles.headerTable}>
          <colgroup>
            <col width="20%" />
            <col width="50%" />
            <col width="30%" />
          </colgroup>
          <thead>
            <tr>
              <th className={styles.th}>
                <button type="button" className={styles.thButton} onClick={() => toggleSort("id")}>
                  ID {getIndicator("id")}
                </button>
              </th>
              <th className={styles.th}>
                <button type="button" className={styles.thButton} onClick={() => toggleSort("name")}>
                  Name {getIndicator("name")}
                </button>
              </th>
              <th className={styles.th}>
                <button type="button" className={styles.thButton} onClick={() => toggleSort("score")}>
                  Score {getIndicator("score")}
                </button>
              </th>
            </tr>
          </thead>
        </table>

        <div
          className={styles.scrollBody}
          onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
        >
          <table className={styles.bodyTable}>
            <colgroup>
              <col width="20%" />
              <col width="50%" />
              <col width="30%" />
            </colgroup>
            <tbody>
              <tr aria-hidden="true">
                <td className={`${styles.spacerCell} ${styles.topSpacer}`} colSpan={3} />
              </tr>

              {visibleRows.map((row, index) => (
                <tr
                  key={row.id}
                  className={`${styles.row} ${(startIndex + index) % 2 === 0 ? styles.rowEven : ""}`}
                >
                  <td className={styles.td}>{row.id}</td>
                  <td className={styles.td}>{row.name}</td>
                  <td className={styles.td}>{row.score}</td>
                </tr>
              ))}

              <tr aria-hidden="true">
                <td className={`${styles.spacerCell} ${styles.bottomSpacer}`} colSpan={3} />
              </tr>
            </tbody>
          </table>
        </div>

        <div className={styles.footer}>
          Overscan buffer: {OVERSCAN} rows on each side. Visible rows rendered right now: {visibleRows.length}.
        </div>
      </div>
    </div>
  );
}

/*
VirtualScrollTable.module.css

.page {
  min-height: 100vh;
  padding: 28px 16px;
  background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
}

.shell {
  max-width: 980px;
  margin: 0 auto;
  background: #ffffff;
  border-radius: 20px;
  overflow: hidden;
}

.header {
  padding: 24px;
  border-bottom: 1px solid #e2e8f0;
}

.headerTable,
.bodyTable {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.scrollBody {
  overflow-y: auto;
}

.thButton {
  width: 100%;
  border: none;
  background: transparent;
  padding: 14px 18px;
  text-align: left;
  cursor: pointer;
}

.td {
  height: 44px;
  padding: 0 18px;
  border-bottom: 1px solid #e2e8f0;
}

.rowEven {
  background: #f8fafc;
}

.spacerCell {
  padding: 0;
  border: none;
}

.topSpacer {}
.bottomSpacer {}
.footer {
  padding: 16px 24px 22px;
}
*/
