import React, { useState, useRef, useCallback, useMemo, useEffect } from 'react';

interface RowData {
  id: number;
  name: string;
  age: number;
  score: number;
}

type SortKey = keyof Pick<RowData, 'name' | 'age' | 'score'>;
type SortDir = 'asc' | 'desc';

const ROW_HEIGHT = 40;
const HEADER_HEIGHT = 44;
const OVERSCAN = 10;
const TOTAL_ROWS = 10000;

function generateData(): RowData[] {
  const names = ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank', 'Grace', 'Hank', 'Ivy', 'Jack'];
  const data: RowData[] = [];
  for (let i = 0; i < TOTAL_ROWS; i++) {
    data.push({
      id: i + 1,
      name: `${names[i % names.length]}_${i + 1}`,
      age: 18 + (i * 7 + 3) % 50,
      score: Math.round(((i * 13 + 7) % 1000) / 10),
    });
  }
  return data;
}

const VirtualScrollTable: React.FC = () => {
  const [data] = useState<RowData[]>(generateData);
  const [sortKey, setSortKey] = useState<SortKey>('name');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerHeight, setContainerHeight] = useState(600);

  useEffect(() => {
    const updateHeight = () => {
      setContainerHeight(Math.min(600, window.innerHeight - 120));
    };
    updateHeight();
    window.addEventListener('resize', updateHeight);
    return () => window.removeEventListener('resize', updateHeight);
  }, []);

  const sortedData = useMemo(() => {
    const sorted = [...data].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortDir === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDir === 'asc' ? aVal - bVal : bVal - aVal;
      }
      return 0;
    });
    return sorted;
  }, [data, sortKey, sortDir]);

  const visibleHeight = containerHeight - HEADER_HEIGHT;
  const totalHeight = sortedData.length * ROW_HEIGHT;
  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const endIndex = Math.min(
    sortedData.length,
    Math.ceil((scrollTop + visibleHeight) / ROW_HEIGHT) + OVERSCAN
  );

  const visibleRows = sortedData.slice(startIndex, endIndex);

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  }, []);

  const handleSort = useCallback((key: SortKey) => {
    setSortKey(prev => {
      if (prev === key) {
        setSortDir(d => d === 'asc' ? 'desc' : 'asc');
        return prev;
      }
      setSortDir('asc');
      return key;
    });
  }, []);

  const getSortIndicator = (key: SortKey): string => {
    if (sortKey !== key) return ' ↕';
    return sortDir === 'asc' ? ' ↑' : ' ↓';
  };

  return (
    <div className={styles.wrapper}>
      <h2 className={styles.title}>Virtual Scroll Table ({TOTAL_ROWS.toLocaleString()} rows)</h2>
      <div
        className={styles.container}
        style={{ height: containerHeight }}
      >
        <div className={styles.header} style={{ height: HEADER_HEIGHT }}>
          <div className={styles.headerCell} style={{ width: '20%' }}>#</div>
          <div
            className={`${styles.headerCell} ${styles.sortable}`}
            style={{ width: '30%' }}
            onClick={() => handleSort('name')}
          >
            Name{getSortIndicator('name')}
          </div>
          <div
            className={`${styles.headerCell} ${styles.sortable}`}
            style={{ width: '25%' }}
            onClick={() => handleSort('age')}
          >
            Age{getSortIndicator('age')}
          </div>
          <div
            className={`${styles.headerCell} ${styles.sortable}`}
            style={{ width: '25%' }}
            onClick={() => handleSort('score')}
          >
            Score{getSortIndicator('score')}
          </div>
        </div>
        <div
          className={styles.scrollArea}
          style={{ height: containerHeight - HEADER_HEIGHT }}
          onScroll={handleScroll}
          ref={containerRef}
        >
          <div className={styles.scrollContent} style={{ height: totalHeight }}>
            {visibleRows.map((row, i) => {
              const actualIndex = startIndex + i;
              return (
                <div
                  key={row.id}
                  className={`${styles.row} ${actualIndex % 2 === 0 ? styles.rowEven : styles.rowOdd}`}
                  style={{
                    position: 'absolute',
                    top: actualIndex * ROW_HEIGHT,
                    height: ROW_HEIGHT,
                    width: '100%',
                  }}
                >
                  <div className={styles.cell} style={{ width: '20%' }}>{row.id}</div>
                  <div className={styles.cell} style={{ width: '30%' }}>{row.name}</div>
                  <div className={styles.cell} style={{ width: '25%' }}>{row.age}</div>
                  <div className={styles.cell} style={{ width: '25%' }}>{row.score}</div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, string> = {} as any;

export default VirtualScrollTable;

/*
=== VirtualScrollTable.module.css ===

.wrapper {
  max-width: 800px;
  margin: 20px auto;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.title {
  text-align: center;
  color: #333;
  margin-bottom: 16px;
  font-size: 20px;
}

.container {
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.header {
  display: flex;
  background: #f5f5f5;
  border-bottom: 2px solid #ddd;
  position: sticky;
  top: 0;
  z-index: 10;
}

.headerCell {
  display: flex;
  align-items: center;
  padding: 0 12px;
  font-weight: 600;
  font-size: 14px;
  color: #555;
  box-sizing: border-box;
}

.sortable {
  cursor: pointer;
  user-select: none;
}

.sortable:hover {
  background: #e8e8e8;
}

.scrollArea {
  overflow-y: auto;
  position: relative;
}

.scrollContent {
  position: relative;
  width: 100%;
}

.row {
  display: flex;
  align-items: center;
  box-sizing: border-box;
  border-bottom: 1px solid #f0f0f0;
}

.rowEven {
  background: #fff;
}

.rowOdd {
  background: #fafafa;
}

.cell {
  padding: 0 12px;
  font-size: 13px;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  box-sizing: border-box;
}
*/
