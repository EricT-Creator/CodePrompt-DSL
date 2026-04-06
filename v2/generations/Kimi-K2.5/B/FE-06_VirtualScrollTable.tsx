import React, { useState, useRef, useEffect, useCallback } from 'react';
import styles from './VirtualScrollTable.module.css';

interface Row {
  id: number;
  name: string;
  email: string;
  age: number;
}

const ROW_HEIGHT = 40;
const TABLE_HEIGHT = 400;
const OVERSCAN = 5;
const TOTAL_ROWS = 10000;

function generateData(count: number): Row[] {
  return Array.from({ length: count }, (_, i) => ({
    id: i + 1,
    name: `User ${i + 1}`,
    email: `user${i + 1}@example.com`,
    age: 20 + (i % 50),
  }));
}

type SortKey = 'name' | 'email' | 'age';
type SortOrder = 'asc' | 'desc';

export default function VirtualScrollTable() {
  const [data] = useState<Row[]>(() => generateData(TOTAL_ROWS));
  const [sortKey, setSortKey] = useState<SortKey>('id' as SortKey);
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const sortedData = React.useMemo(() => {
    const sorted = [...data];
    sorted.sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });
    return sorted;
  }, [data, sortKey, sortOrder]);

  const visibleStart = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const visibleEnd = Math.min(
    sortedData.length,
    Math.ceil((scrollTop + TABLE_HEIGHT) / ROW_HEIGHT) + OVERSCAN
  );
  const visibleData = sortedData.slice(visibleStart, visibleEnd);

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  }, []);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortOrder('asc');
    }
  };

  const getSortIndicator = (key: SortKey) => {
    if (sortKey !== key) return '⇅';
    return sortOrder === 'asc' ? '↑' : '↓';
  };

  return (
    <div className={styles.container}>
      <h2 className={styles.title}>Virtual Scroll Table ({TOTAL_ROWS.toLocaleString()} rows)</h2>
      <div
        ref={containerRef}
        className={styles.tableContainer}
        onScroll={handleScroll}
        style={{ height: TABLE_HEIGHT, overflow: 'auto' }}
      >
        <div style={{ height: sortedData.length * ROW_HEIGHT, position: 'relative' }}>
          <table className={styles.table} style={{ position: 'absolute', top: 0, left: 0, right: 0 }}>
            <thead className={styles.header}>
              <tr>
                <th className={styles.th}>ID</th>
                <th className={styles.th} onClick={() => handleSort('name')}>
                  Name {getSortIndicator('name')}
                </th>
                <th className={styles.th} onClick={() => handleSort('email')}>
                  Email {getSortIndicator('email')}
                </th>
                <th className={styles.th} onClick={() => handleSort('age')}>
                  Age {getSortIndicator('age')}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ height: visibleStart * ROW_HEIGHT }}>
                <td colSpan={4}></td>
              </tr>
              {visibleData.map((row) => (
                <tr
                  key={row.id}
                  className={styles.row}
                  style={{ height: ROW_HEIGHT }}
                >
                  <td className={styles.td}>{row.id}</td>
                  <td className={styles.td}>{row.name}</td>
                  <td className={styles.td}>{row.email}</td>
                  <td className={styles.td}>{row.age}</td>
                </tr>
              ))}
              <tr style={{ height: (sortedData.length - visibleEnd) * ROW_HEIGHT }}>
                <td colSpan={4}></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div className={styles.info}>
        Showing rows {visibleStart + 1} - {visibleEnd} of {sortedData.length}
      </div>
    </div>
  );
}

/* CSS Module Content - VirtualScrollTable.module.css:
.container {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.title {
  margin-bottom: 16px;
  font-size: 1.5rem;
  color: #333;
}

.tableContainer {
  border: 1px solid #ddd;
  border-radius: 8px;
  background: white;
}

.table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.header {
  position: sticky;
  top: 0;
  background: #f5f5f5;
  z-index: 1;
}

.th {
  padding: 12px 16px;
  text-align: left;
  font-weight: 600;
  border-bottom: 2px solid #ddd;
  cursor: pointer;
  user-select: none;
}

.th:hover {
  background: #e0e0e0;
}

.row:hover {
  background: #f9f9f9;
}

.td {
  padding: 10px 16px;
  border-bottom: 1px solid #eee;
}

.info {
  margin-top: 12px;
  color: #666;
  font-size: 0.9rem;
}
*/
