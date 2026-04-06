import React, { useState, useRef, useCallback, useEffect, useMemo } from 'react';

interface RowData {
  id: number;
  name: string;
  age: number;
  score: number;
}

type SortKey = 'name' | 'age' | 'score';
type SortDir = 'asc' | 'desc';

const ROW_HEIGHT = 36;
const HEADER_HEIGHT = 40;
const OVERSCAN = 5;
const TOTAL_ROWS = 10000;

function generateData(count: number): RowData[] {
  const firstNames = ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank', 'Grace', 'Henry', 'Iris', 'Jack'];
  const lastNames = ['Smith', 'Johnson', 'Brown', 'Taylor', 'Anderson', 'Thomas', 'Moore', 'Martin', 'Lee', 'Clark'];
  const data: RowData[] = [];
  for (let i = 0; i < count; i++) {
    data.push({
      id: i + 1,
      name: `${firstNames[i % firstNames.length]} ${lastNames[Math.floor(i / firstNames.length) % lastNames.length]}`,
      age: 18 + (i * 7 + 3) % 52,
      score: Math.round(((i * 13 + 7) % 1000) / 10) / 10,
    });
  }
  return data;
}

const VirtualScrollTable: React.FC = () => {
  const [sortKey, setSortKey] = useState<SortKey>('name');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerHeight, setContainerHeight] = useState(600);

  const rawData = useMemo(() => generateData(TOTAL_ROWS), []);

  const sortedData = useMemo(() => {
    const sorted = [...rawData];
    sorted.sort((a, b) => {
      let cmp = 0;
      if (sortKey === 'name') {
        cmp = a.name.localeCompare(b.name);
      } else if (sortKey === 'age') {
        cmp = a.age - b.age;
      } else {
        cmp = a.score - b.score;
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return sorted;
  }, [rawData, sortKey, sortDir]);

  useEffect(() => {
    const el = containerRef.current;
    if (el) {
      setContainerHeight(el.clientHeight - HEADER_HEIGHT);
    }
  }, []);

  const handleSort = useCallback((key: SortKey) => {
    setSortKey(prev => {
      if (prev === key) {
        setSortDir(d => (d === 'asc' ? 'desc' : 'asc'));
        return prev;
      }
      setSortDir('asc');
      return key;
    });
  }, []);

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop((e.target as HTMLDivElement).scrollTop);
  }, []);

  const totalHeight = sortedData.length * ROW_HEIGHT;
  const visibleCount = Math.ceil(containerHeight / ROW_HEIGHT);
  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const endIndex = Math.min(sortedData.length - 1, Math.floor(scrollTop / ROW_HEIGHT) + visibleCount + OVERSCAN);

  const visibleRows = sortedData.slice(startIndex, endIndex + 1);

  const getSortIndicator = (key: SortKey): string => {
    if (sortKey !== key) return ' ↕';
    return sortDir === 'asc' ? ' ↑' : ' ↓';
  };

  return (
    <div ref={containerRef} className="vst-container">
      <table className="vst-table">
        <thead>
          <tr className="vst-header-row">
            <th className="vst-th vst-th-name" onClick={() => handleSort('name')}>
              Name{getSortIndicator('name')}
            </th>
            <th className="vst-th vst-th-age" onClick={() => handleSort('age')}>
              Age{getSortIndicator('age')}
            </th>
            <th className="vst-th vst-th-score" onClick={() => handleSort('score')}>
              Score{getSortIndicator('score')}
            </th>
          </tr>
        </thead>
      </table>
      <div className="vst-scroll-area" onScroll={handleScroll}>
        <div className="vst-spacer" style={{ height: `${totalHeight}px` }}>
          <table className="vst-table vst-body-table" style={{ transform: `translateY(${startIndex * ROW_HEIGHT}px)` }}>
            <tbody>
              {visibleRows.map((row, i) => (
                <tr key={row.id} className={`vst-row ${(startIndex + i) % 2 === 0 ? 'vst-row-even' : 'vst-row-odd'}`}>
                  <td className="vst-td vst-td-name">{row.name}</td>
                  <td className="vst-td vst-td-age">{row.age}</td>
                  <td className="vst-td vst-td-score">{row.score}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="vst-footer">
        Showing rows {startIndex + 1}–{endIndex + 1} of {sortedData.length.toLocaleString()}
      </div>
    </div>
  );
};

export default VirtualScrollTable;

/*
=== CSS Module: VirtualScrollTable.module.css ===

.vst-container {
  width: 100%;
  max-width: 700px;
  margin: 20px auto;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  display: flex;
  flex-direction: column;
  height: 600px;
  background: #fff;
}

.vst-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.vst-header-row {
  height: 40px;
}

.vst-th {
  padding: 10px 16px;
  text-align: left;
  font-weight: 600;
  font-size: 13px;
  color: #374151;
  background: #f3f4f6;
  border-bottom: 2px solid #d1d5db;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}

.vst-th:hover {
  background: #e5e7eb;
}

.vst-th-name {
  width: 50%;
}

.vst-th-age {
  width: 20%;
}

.vst-th-score {
  width: 30%;
}

.vst-scroll-area {
  flex: 1;
  overflow-y: auto;
  position: relative;
}

.vst-spacer {
  position: relative;
}

.vst-body-table {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
}

.vst-row {
  height: 36px;
}

.vst-row-even {
  background: #ffffff;
}

.vst-row-odd {
  background: #f9fafb;
}

.vst-row:hover {
  background: #eff6ff;
}

.vst-td {
  padding: 8px 16px;
  font-size: 13px;
  color: #4b5563;
  border-bottom: 1px solid #f3f4f6;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.vst-td-name {
  width: 50%;
}

.vst-td-age {
  width: 20%;
}

.vst-td-score {
  width: 30%;
}

.vst-footer {
  padding: 8px 16px;
  font-size: 12px;
  color: #6b7280;
  background: #f9fafb;
  border-top: 1px solid #e5e7eb;
  text-align: center;
}
*/
