import React, { useEffect, useMemo, useRef, useState } from "react";

type SortKey = "id" | "name" | "score";
type SortDirection = "asc" | "desc";

type RowData = {
  id: number;
  name: string;
  score: number;
};

const styles = {
  page: "VirtualScrollTable_page__a1",
  card: "VirtualScrollTable_card__a1",
  title: "VirtualScrollTable_title__a1",
  subtitle: "VirtualScrollTable_subtitle__a1",
  table: "VirtualScrollTable_table__a1",
  headerRow: "VirtualScrollTable_headerRow__a1",
  headerButton: "VirtualScrollTable_headerButton__a1",
  headerButtonActive: "VirtualScrollTable_headerButtonActive__a1",
  scroller: "VirtualScrollTable_scroller__a1",
  spacer: "VirtualScrollTable_spacer__a1",
  row: "VirtualScrollTable_row__a1",
  cell: "VirtualScrollTable_cell__a1",
  numeric: "VirtualScrollTable_numeric__a1",
  footer: "VirtualScrollTable_footer__a1",
} as const;

const moduleCss = `
.${styles.page} {
  min-height: 100vh;
  padding: 32px 18px;
  background: linear-gradient(180deg, #f3f6fb 0%, #edf3ff 100%);
  font-family: Arial, Helvetica, sans-serif;
  color: #15223b;
}

.${styles.card} {
  max-width: 980px;
  margin: 0 auto;
  background: #ffffff;
  border: 1px solid #d7dfef;
  border-radius: 24px;
  box-shadow: 0 24px 64px rgba(20, 46, 117, 0.12);
  overflow: hidden;
}

.${styles.title} {
  margin: 0;
  padding: 24px 24px 8px;
  font-size: 30px;
  font-weight: 700;
}

.${styles.subtitle} {
  margin: 0;
  padding: 0 24px 22px;
  color: #5b6882;
  line-height: 1.6;
  border-bottom: 1px solid #e6ebf5;
}

.${styles.table} {
  padding: 0 18px 18px;
}

.${styles.headerRow} {
  display: grid;
  grid-template-columns: 140px minmax(260px, 1fr) 180px;
  gap: 12px;
  padding: 18px 6px 12px;
  position: sticky;
  top: 0;
  z-index: 2;
  background: #ffffff;
}

.${styles.headerButton} {
  appearance: none;
  border: 1px solid #d7dfef;
  background: #f6f8fc;
  color: #33415e;
  font-size: 14px;
  font-weight: 700;
  border-radius: 14px;
  padding: 12px 14px;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.16s ease, background-color 0.16s ease, transform 0.16s ease;
}

.${styles.headerButton}:hover {
  border-color: #7c95e8;
  background: #eff4ff;
  transform: translateY(-1px);
}

.${styles.headerButtonActive} {
  border-color: #4560df;
  background: #eaf0ff;
  color: #2441c8;
}

.${styles.scroller} {
  height: 480px;
  overflow-y: auto;
  border: 1px solid #e0e6f3;
  border-radius: 20px;
  background: #fbfcff;
}

.${styles.spacer} {
  width: 100%;
}

.${styles.row} {
  display: grid;
  grid-template-columns: 140px minmax(260px, 1fr) 180px;
  gap: 12px;
  align-items: center;
  min-height: 46px;
  padding: 0 12px;
  border-bottom: 1px solid #edf1f8;
  background: #ffffff;
}

.${styles.row}:nth-child(odd) {
  background: #f9fbff;
}

.${styles.cell} {
  padding: 12px 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.${styles.numeric} {
  font-variant-numeric: tabular-nums;
}

.${styles.footer} {
  padding: 14px 6px 0;
  color: #5c6984;
  font-size: 14px;
}
`;

const STYLE_ELEMENT_ID = "virtual-scroll-table-module-style";
const ROW_HEIGHT = 46;
const VIEWPORT_HEIGHT = 480;
const BUFFER_SIZE = 8;
const TOTAL_ROWS = 10000;

function ensureModuleStyle(): void {
  if (typeof document === "undefined") {
    return;
  }
  if (document.getElementById(STYLE_ELEMENT_ID)) {
    return;
  }
  const styleElement = document.createElement("style");
  styleElement.id = STYLE_ELEMENT_ID;
  styleElement.textContent = moduleCss;
  document.head.appendChild(styleElement);
}

function createRows(): RowData[] {
  const prefixes = ["北辰", "清河", "远山", "星屿", "南风", "明川", "云栖", "霁月"];
  const suffixes = ["项目", "任务", "计划", "模块", "站点", "清单", "小组", "工单"];

  return Array.from({ length: TOTAL_ROWS }, (_, index) => ({
    id: index + 1,
    name: `${prefixes[index % prefixes.length]}${suffixes[index % suffixes.length]}-${String(index + 1).padStart(5, "0")}`,
    score: (index * 37 + 13) % 1000,
  }));
}

function compareValue(
  left: string | number,
  right: string | number,
  direction: SortDirection,
): number {
  const result = left < right ? -1 : left > right ? 1 : 0;
  return direction === "asc" ? result : -result;
}

export default function VirtualScrollTable() {
  const [sortKey, setSortKey] = useState<SortKey>("id");
  const [direction, setDirection] = useState<SortDirection>("asc");
  const [scrollTop, setScrollTop] = useState(0);
  const topSpacerRef = useRef<HTMLDivElement | null>(null);
  const bottomSpacerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    ensureModuleStyle();
  }, []);

  const allRows = useMemo(() => createRows(), []);

  const sortedRows = useMemo(() => {
    return [...allRows].sort((a, b) => {
      if (sortKey === "id") {
        return compareValue(a.id, b.id, direction);
      }
      if (sortKey === "name") {
        return compareValue(a.name, b.name, direction);
      }
      return compareValue(a.score, b.score, direction);
    });
  }, [allRows, direction, sortKey]);

  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - BUFFER_SIZE);
  const visibleCount = Math.ceil(VIEWPORT_HEIGHT / ROW_HEIGHT) + BUFFER_SIZE * 2;
  const endIndex = Math.min(sortedRows.length, startIndex + visibleCount);
  const visibleRows = sortedRows.slice(startIndex, endIndex);
  const topSpacerHeight = startIndex * ROW_HEIGHT;
  const bottomSpacerHeight = Math.max(0, (sortedRows.length - endIndex) * ROW_HEIGHT);

  useEffect(() => {
    if (topSpacerRef.current) {
      topSpacerRef.current.style.height = `${topSpacerHeight}px`;
    }
    if (bottomSpacerRef.current) {
      bottomSpacerRef.current.style.height = `${bottomSpacerHeight}px`;
    }
  }, [bottomSpacerHeight, topSpacerHeight]);

  const requestSort = (nextKey: SortKey) => {
    if (nextKey === sortKey) {
      setDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(nextKey);
    setDirection("asc");
  };

  const getSortLabel = (key: SortKey) => {
    if (sortKey !== key) {
      return "未排序";
    }
    return direction === "asc" ? "升序" : "降序";
  };

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <h1 className={styles.title}>万行虚拟滚动表格</h1>
        <p className={styles.subtitle}>
          固定表头、三列排序、仅渲染可见区域与缓冲区。当前显示
          {visibleRows.length} 行，可滚动浏览 10000 条记录。
        </p>

        <div className={styles.table}>
          <div className={styles.headerRow} role="row">
            {([
              ["id", "编号"],
              ["name", "名称"],
              ["score", "评分"],
            ] as Array<[SortKey, string]>).map(([key, label]) => (
              <button
                key={key}
                type="button"
                className={[
                  styles.headerButton,
                  sortKey === key ? styles.headerButtonActive : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                onClick={() => requestSort(key)}
              >
                {label} · {getSortLabel(key)}
              </button>
            ))}
          </div>

          <div
            className={styles.scroller}
            onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
          >
            <div ref={topSpacerRef} className={styles.spacer} />
            {visibleRows.map((row) => (
              <div key={row.id} className={styles.row} role="row">
                <div className={`${styles.cell} ${styles.numeric}`}>{row.id}</div>
                <div className={styles.cell}>{row.name}</div>
                <div className={`${styles.cell} ${styles.numeric}`}>{row.score}</div>
              </div>
            ))}
            <div ref={bottomSpacerRef} className={styles.spacer} />
          </div>

          <div className={styles.footer}>
            已渲染区间：第 {startIndex + 1} 行到第 {endIndex} 行，缓冲区大小 {BUFFER_SIZE}。
          </div>
        </div>
      </div>
    </div>
  );
}

/* FE-06_VirtualScrollTable.module.css
.VirtualScrollTable_page__a1 {
  min-height: 100vh;
  padding: 32px 18px;
  background: linear-gradient(180deg, #f3f6fb 0%, #edf3ff 100%);
  font-family: Arial, Helvetica, sans-serif;
  color: #15223b;
}

.VirtualScrollTable_card__a1 {
  max-width: 980px;
  margin: 0 auto;
  background: #ffffff;
  border: 1px solid #d7dfef;
  border-radius: 24px;
  box-shadow: 0 24px 64px rgba(20, 46, 117, 0.12);
  overflow: hidden;
}

.VirtualScrollTable_title__a1 {
  margin: 0;
  padding: 24px 24px 8px;
  font-size: 30px;
  font-weight: 700;
}

.VirtualScrollTable_subtitle__a1 {
  margin: 0;
  padding: 0 24px 22px;
  color: #5b6882;
  line-height: 1.6;
  border-bottom: 1px solid #e6ebf5;
}

.VirtualScrollTable_table__a1 {
  padding: 0 18px 18px;
}

.VirtualScrollTable_headerRow__a1 {
  display: grid;
  grid-template-columns: 140px minmax(260px, 1fr) 180px;
  gap: 12px;
  padding: 18px 6px 12px;
  position: sticky;
  top: 0;
  z-index: 2;
  background: #ffffff;
}

.VirtualScrollTable_headerButton__a1 {
  appearance: none;
  border: 1px solid #d7dfef;
  background: #f6f8fc;
  color: #33415e;
  font-size: 14px;
  font-weight: 700;
  border-radius: 14px;
  padding: 12px 14px;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.16s ease, background-color 0.16s ease, transform 0.16s ease;
}

.VirtualScrollTable_headerButton__a1:hover {
  border-color: #7c95e8;
  background: #eff4ff;
  transform: translateY(-1px);
}

.VirtualScrollTable_headerButtonActive__a1 {
  border-color: #4560df;
  background: #eaf0ff;
  color: #2441c8;
}

.VirtualScrollTable_scroller__a1 {
  height: 480px;
  overflow-y: auto;
  border: 1px solid #e0e6f3;
  border-radius: 20px;
  background: #fbfcff;
}

.VirtualScrollTable_spacer__a1 {
  width: 100%;
}

.VirtualScrollTable_row__a1 {
  display: grid;
  grid-template-columns: 140px minmax(260px, 1fr) 180px;
  gap: 12px;
  align-items: center;
  min-height: 46px;
  padding: 0 12px;
  border-bottom: 1px solid #edf1f8;
  background: #ffffff;
}

.VirtualScrollTable_row__a1:nth-child(odd) {
  background: #f9fbff;
}

.VirtualScrollTable_cell__a1 {
  padding: 12px 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.VirtualScrollTable_numeric__a1 {
  font-variant-numeric: tabular-nums;
}

.VirtualScrollTable_footer__a1 {
  padding: 14px 6px 0;
  color: #5c6984;
  font-size: 14px;
}
*/
