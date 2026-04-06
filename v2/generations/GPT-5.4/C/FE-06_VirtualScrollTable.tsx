import React, { useEffect, useMemo, useRef, useState } from 'react';

const BASE_STYLE_ID = 'fe06-virtual-scroll-table-base';
const DYNAMIC_STYLE_ID = 'fe06-virtual-scroll-table-dynamic';
const TOTAL_ROWS = 10000;
const ROW_HEIGHT = 42;
const VIEWPORT_HEIGHT = 420;
const OVERSCAN = 6;

type SortKey = 'id' | 'score' | 'hours';
type SortDirection = 'asc' | 'desc';

type RowItem = {
  id: number;
  score: number;
  hours: number;
};

function ensureBaseStyles() {
  if (typeof document === 'undefined' || document.getElementById(BASE_STYLE_ID)) {
    return;
  }
  const style = document.createElement('style');
  style.id = BASE_STYLE_ID;
  style.textContent = `
    .vstShell {
      max-width: 760px;
      margin: 28px auto;
      border: 1px solid #d7deea;
      border-radius: 14px;
      overflow: hidden;
      background: #ffffff;
      box-shadow: 0 16px 36px rgba(15, 23, 42, 0.08);
      font-family: Arial, Helvetica, sans-serif;
      color: #13293d;
    }
    .vstHeaderBlock {
      padding: 18px 20px 10px;
      border-bottom: 1px solid #e7edf5;
      background: linear-gradient(180deg, #f9fbff 0%, #f4f7fb 100%);
    }
    .vstTitle {
      margin: 0;
      font-size: 24px;
      font-weight: 700;
    }
    .vstSubtitle {
      margin: 6px 0 0;
      font-size: 13px;
      color: #52667a;
    }
    .vstTable {
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }
    .vstHeadCell,
    .vstCell {
      padding: 0 16px;
      text-align: left;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      box-sizing: border-box;
    }
    .vstHeadCell {
      height: 48px;
      background: #0f172a;
      color: #ffffff;
      font-size: 13px;
      font-weight: 700;
      border-bottom: 1px solid #0b1220;
    }
    .vstSortButton {
      appearance: none;
      width: 100%;
      height: 48px;
      border: 0;
      background: transparent;
      color: inherit;
      text-align: left;
      font: inherit;
      cursor: pointer;
    }
    .vstSortButton:hover {
      color: #93c5fd;
    }
    .vstViewport {
      height: 420px;
      overflow-y: auto;
      overflow-x: hidden;
      background: #ffffff;
    }
    .vstRow {
      height: 42px;
      border-bottom: 1px solid #edf2f7;
    }
    .vstRow:nth-child(even) {
      background: #f8fbff;
    }
    .vstRow:hover {
      background: #ebf4ff;
    }
    .vstCell {
      height: 42px;
      font-size: 13px;
      color: #243b53;
    }
    .vstSpacerRow {
      border: 0;
    }
    .vstSpacerCell {
      padding: 0;
      border: 0;
      height: 0;
      background: transparent;
    }
    .vstFooter {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 12px 18px 16px;
      border-top: 1px solid #e7edf5;
      font-size: 12px;
      color: #52667a;
      background: #f9fbff;
    }
  `;
  document.head.appendChild(style);
}

function updateDynamicStyles(topPadding: number, bottomPadding: number) {
  if (typeof document === 'undefined') {
    return;
  }
  let style = document.getElementById(DYNAMIC_STYLE_ID) as HTMLStyleElement | null;
  if (!style) {
    style = document.createElement('style');
    style.id = DYNAMIC_STYLE_ID;
    document.head.appendChild(style);
  }
  style.textContent = `
    .vstTopSpacer .vstSpacerCell { height: ${topPadding}px; }
    .vstBottomSpacer .vstSpacerCell { height: ${bottomPadding}px; }
  `;
}

function buildRows(): RowItem[] {
  return Array.from({ length: TOTAL_ROWS }, (_, index) => ({
    id: index + 1,
    score: (index * 37 + 91) % 1000,
    hours: (index * 11 + 17) % 240,
  }));
}

function sortRows(rows: RowItem[], key: SortKey, direction: SortDirection) {
  const next = [...rows];
  next.sort((left, right) => {
    const multiplier = direction === 'asc' ? 1 : -1;
    return (left[key] - right[key]) * multiplier;
  });
  return next;
}

export default function VirtualScrollTable() {
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const rows = useMemo(() => buildRows(), []);
  const [sortKey, setSortKey] = useState<SortKey>('id');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [scrollTop, setScrollTop] = useState(0);

  useEffect(() => {
    ensureBaseStyles();
  }, []);

  const sortedRows = useMemo(() => sortRows(rows, sortKey, sortDirection), [rows, sortKey, sortDirection]);
  const visibleCount = Math.ceil(VIEWPORT_HEIGHT / ROW_HEIGHT);
  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const endIndex = Math.min(sortedRows.length, startIndex + visibleCount + OVERSCAN * 2);
  const visibleRows = sortedRows.slice(startIndex, endIndex);
  const topPadding = startIndex * ROW_HEIGHT;
  const bottomPadding = (sortedRows.length - endIndex) * ROW_HEIGHT;

  useEffect(() => {
    updateDynamicStyles(topPadding, bottomPadding);
  }, [topPadding, bottomPadding]);

  const changeSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setSortKey(key);
    setSortDirection('asc');
  };

  const sortLabel = (key: SortKey, label: string) => {
    if (sortKey !== key) {
      return `${label} ↕`;
    }
    return `${label} ${sortDirection === 'asc' ? '↑' : '↓'}`;
  };

  return (
    <section className="vstShell" aria-label="Virtual scroll table">
      <div className="vstHeaderBlock">
        <h2 className="vstTitle">Virtual Scroll Metrics</h2>
        <p className="vstSubtitle">10,000 rows · fixed header · 3 sortable columns · visible rows plus overscan only.</p>
      </div>
      <table className="vstTable" aria-hidden="true">
        <thead>
          <tr>
            <th className="vstHeadCell">
              <button className="vstSortButton" type="button" onClick={() => changeSort('id')}>
                {sortLabel('id', 'Ticket ID')}
              </button>
            </th>
            <th className="vstHeadCell">
              <button className="vstSortButton" type="button" onClick={() => changeSort('score')}>
                {sortLabel('score', 'Score')}
              </button>
            </th>
            <th className="vstHeadCell">
              <button className="vstSortButton" type="button" onClick={() => changeSort('hours')}>
                {sortLabel('hours', 'Open Hours')}
              </button>
            </th>
          </tr>
        </thead>
      </table>
      <div
        ref={viewportRef}
        className="vstViewport"
        onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
      >
        <table className="vstTable">
          <tbody>
            <tr className="vstSpacerRow vstTopSpacer" aria-hidden="true">
              <td className="vstSpacerCell" colSpan={3} />
            </tr>
            {visibleRows.map((row) => (
              <tr key={row.id} className="vstRow">
                <td className="vstCell">#{row.id.toString().padStart(5, '0')}</td>
                <td className="vstCell">{row.score}</td>
                <td className="vstCell">{row.hours}</td>
              </tr>
            ))}
            <tr className="vstSpacerRow vstBottomSpacer" aria-hidden="true">
              <td className="vstSpacerCell" colSpan={3} />
            </tr>
          </tbody>
        </table>
      </div>
      <div className="vstFooter">
        <span>Rendered rows: {visibleRows.length}</span>
        <span>Window: {startIndex + 1}-{Math.min(endIndex, TOTAL_ROWS)} / {TOTAL_ROWS}</span>
      </div>
    </section>
  );
}

/*
VirtualScrollTable.module.css

.vstShell {
  max-width: 760px;
  margin: 28px auto;
  border: 1px solid #d7deea;
  border-radius: 14px;
  overflow: hidden;
  background: #ffffff;
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.08);
  font-family: Arial, Helvetica, sans-serif;
  color: #13293d;
}

.vstHeaderBlock {
  padding: 18px 20px 10px;
  border-bottom: 1px solid #e7edf5;
  background: linear-gradient(180deg, #f9fbff 0%, #f4f7fb 100%);
}

.vstTable {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.vstViewport {
  height: 420px;
  overflow-y: auto;
  overflow-x: hidden;
  background: #ffffff;
}

.vstHeadCell {
  height: 48px;
  background: #0f172a;
  color: #ffffff;
  font-size: 13px;
  font-weight: 700;
}

.vstSortButton {
  appearance: none;
  width: 100%;
  height: 48px;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  font: inherit;
  cursor: pointer;
}

.vstRow {
  height: 42px;
  border-bottom: 1px solid #edf2f7;
}

.vstCell {
  height: 42px;
  font-size: 13px;
  color: #243b53;
}

.vstSpacerCell {
  padding: 0;
  border: 0;
  background: transparent;
}

.vstFooter {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 18px 16px;
  border-top: 1px solid #e7edf5;
  font-size: 12px;
  color: #52667a;
  background: #f9fbff;
}
*/
