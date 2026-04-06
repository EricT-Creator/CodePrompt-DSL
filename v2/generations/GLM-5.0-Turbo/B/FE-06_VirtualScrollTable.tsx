import React, { useState, useRef, useCallback, useEffect, useMemo } from 'react';

interface RowData {
  id: number;
  name: string;
  email: string;
  score: number;
}

function generateRows(count: number): RowData[] {
  const rows: RowData[] = [];
  for (let i = 0; i < count; i++) {
    rows.push({
      id: i + 1,
      name: `User_${String(i + 1).padStart(4, '0')}`,
      email: `user${i + 1}@example.com`,
      score: Math.floor(Math.random() * 100),
    });
  }
  return rows;
}

const ROW_HEIGHT = 40;
const HEADER_HEIGHT = 48;
const OVERSCAN = 5;

/* ===== CSS Module content =====
.virtual-table-container {
  width: 800px;
  max-height: 600px;
  margin: 24px auto;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}

.virtual-table-header {
  display: flex;
  align-items: center;
  height: 48px;
  background: #f5f7fa;
  border-bottom: 1px solid #ddd;
  padding: 0;
  position: sticky;
  top: 0;
  z-index: 10;
}

.virtual-table-header-cell {
  flex: 1;
  padding: 0 16px;
  font-weight: 600;
  font-size: 13px;
  color: #555;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  cursor: pointer;
  user-select: none;
  display: flex;
  align-items: center;
  gap: 6px;
}

.virtual-table-header-cell:hover {
  color: #333;
}

.virtual-table-header-cell.sort-asc::after {
  content: '▲';
  font-size: 10px;
}

.virtual-table-header-cell.sort-desc::after {
  content: '▼';
  font-size: 10px;
}

.virtual-table-header-cell.col-id {
  flex: 0 0 80px;
}

.virtual-table-body {
  height: calc(600px - 48px);
  overflow-y: auto;
  position: relative;
}

.virtual-table-row {
  display: flex;
  align-items: center;
  height: 40px;
  border-bottom: 1px solid #f0f0f0;
  padding: 0;
}

.virtual-table-row:hover {
  background: #f8fafc;
}

.virtual-table-row:nth-child(even) {
  background: #fafbfc;
}

.virtual-table-row:nth-child(even):hover {
  background: #f0f4f8;
}

.virtual-table-cell {
  flex: 1;
  padding: 0 16px;
  font-size: 13px;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.virtual-table-cell.col-id {
  flex: 0 0 80px;
  color: #888;
  font-size: 12px;
}

.virtual-table-spacer {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  pointer-events: none;
}

.virtual-table-visible {
  position: absolute;
  left: 0;
  right: 0;
}

.virtual-table-info {
  padding: 8px 16px;
  background: #f5f7fa;
  border-top: 1px solid #ddd;
  font-size: 12px;
  color: #888;
  display: flex;
  justify-content: space-between;
}
===== End CSS Module ===== */

type SortKey = 'id' | 'name' | 'score';
type SortDir = 'asc' | 'desc';

export default function VirtualScrollTable() {
  const allRows = useMemo(() => generateRows(10000), []);
  const [sortKey, setSortKey] = useState<SortKey>('id');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [scrollTop, setScrollTop] = useState(0);
  const bodyRef = useRef<HTMLDivElement>(null);

  const sortedRows = useMemo(() => {
    const arr = [...allRows];
    arr.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      let cmp = 0;
      if (typeof av === 'string' && typeof bv === 'string') {
        cmp = av.localeCompare(bv);
      } else {
        cmp = (av as number) - (bv as number);
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return arr;
  }, [allRows, sortKey, sortDir]);

  const handleSort = useCallback((key: SortKey) => {
    if (sortKey === key) {
      setSortDir(prev => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  }, [sortKey]);

  const totalHeight = sortedRows.length * ROW_HEIGHT;
  const containerHeight = 600 - HEADER_HEIGHT;

  const startIdx = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const visibleCount = Math.ceil(containerHeight / ROW_HEIGHT);
  const endIdx = Math.min(sortedRows.length, startIdx + visibleCount + OVERSCAN * 2);
  const visibleRows = sortedRows.slice(startIdx, endIdx);

  const handleScroll = useCallback(() => {
    if (bodyRef.current) {
      setScrollTop(bodyRef.current.scrollTop);
    }
  }, []);

  return (
    <div style={{ padding: 24 }}>
      <style>{`
        .virtual-table-container {
          width: 800px;
          max-width: 100%;
          margin: 0 auto;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          border: 1px solid #ddd;
          border-radius: 8px;
          overflow: hidden;
          box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        }
        .virtual-table-header {
          display: flex;
          align-items: center;
          height: 48px;
          background: #f5f7fa;
          border-bottom: 1px solid #ddd;
          padding: 0;
          position: sticky;
          top: 0;
          z-index: 10;
        }
        .virtual-table-header-cell {
          flex: 1;
          padding: 0 16px;
          font-weight: 600;
          font-size: 13px;
          color: #555;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          cursor: pointer;
          user-select: none;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .virtual-table-header-cell:hover {
          color: #333;
          background: #eef1f5;
        }
        .virtual-table-header-cell.col-id {
          flex: 0 0 80px;
        }
        .virtual-table-header-cell.sort-asc::after {
          content: ' ▲';
          font-size: 10px;
          color: #4a90d9;
        }
        .virtual-table-header-cell.sort-desc::after {
          content: ' ▼';
          font-size: 10px;
          color: #4a90d9;
        }
        .virtual-table-body {
          height: 552px;
          overflow-y: auto;
          position: relative;
        }
        .virtual-table-row {
          display: flex;
          align-items: center;
          height: 40px;
          border-bottom: 1px solid #f0f0f0;
          padding: 0;
          box-sizing: border-box;
        }
        .virtual-table-row:hover {
          background: #f8fafc;
        }
        .virtual-table-cell {
          flex: 1;
          padding: 0 16px;
          font-size: 13px;
          color: #333;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          box-sizing: border-box;
        }
        .virtual-table-cell.col-id {
          flex: 0 0 80px;
          color: #888;
          font-size: 12px;
          box-sizing: border-box;
        }
        .virtual-table-spacer {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          pointer-events: none;
        }
        .virtual-table-visible {
          position: absolute;
          left: 0;
          right: 0;
        }
        .virtual-table-info {
          padding: 8px 16px;
          background: #f5f7fa;
          border-top: 1px solid #ddd;
          font-size: 12px;
          color: #888;
          display: flex;
          justify-content: space-between;
        }
      `}</style>
      <div className="virtual-table-container">
        <div className="virtual-table-header">
          <div
            className={`virtual-table-header-cell col-id${sortKey === 'id' ? (sortDir === 'asc' ? ' sort-asc' : ' sort-desc') : ''}`}
            onClick={() => handleSort('id')}
          >
            ID
          </div>
          <div
            className={`virtual-table-header-cell${sortKey === 'name' ? (sortDir === 'asc' ? ' sort-asc' : ' sort-desc') : ''}`}
            onClick={() => handleSort('name')}
          >
            Name
          </div>
          <div
            className={`virtual-table-header-cell${sortKey === 'score' ? (sortDir === 'asc' ? ' sort-asc' : ' sort-desc') : ''}`}
            onClick={() => handleSort('score')}
          >
            Score
          </div>
        </div>
        <div className="virtual-table-body" ref={bodyRef} onScroll={handleScroll}>
          <div className="virtual-table-spacer" style={{ height: totalHeight }} />
          <div className="virtual-table-visible" style={{ top: startIdx * ROW_HEIGHT }}>
            {visibleRows.map((row, i) => (
              <div className="virtual-table-row" key={row.id}>
                <div className="virtual-table-cell col-id">{row.id}</div>
                <div className="virtual-table-cell">{row.name}</div>
                <div className="virtual-table-cell">{row.email}</div>
                <div className="virtual-table-cell">{row.score}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="virtual-table-info">
          <span>Showing {startIdx + 1}-{Math.min(endIdx, sortedRows.length)} of {sortedRows.length}</span>
          <span>Sorted by: {sortKey} ({sortDir})</span>
        </div>
      </div>
    </div>
  );
}
