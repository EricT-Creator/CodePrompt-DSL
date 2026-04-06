import React, { useState, useMemo, useRef, useCallback } from 'react';
import styles from './VirtualScrollTable.module.css';

interface RowData {
  id: number;
  name: string;
  age: number;
  email: string;
}

const ROW_HEIGHT = 40;
const VISIBLE_ROWS = 15;
const OVERSCAN = 5;
const TOTAL_ROWS = 10000;

type SortKey = 'name' | 'age' | 'email';
type SortOrder = 'asc' | 'desc';

export default function VirtualScrollTable() {
  const [data] = useState<RowData[]>(() => {
    return Array.from({ length: TOTAL_ROWS }, (_, i) => ({
      id: i + 1,
      name: `User ${i + 1}`,
      age: 18 + (i % 50),
      email: `user${i + 1}@example.com`,
    }));
  });
  
  const [sortKey, setSortKey] = useState<SortKey>('id' as SortKey);
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const sortedData = useMemo(() => {
    const sorted = [...data];
    sorted.sort((a, b) => {
      let aVal: string | number;
      let bVal: string | number;
      
      if (sortKey === 'name') {
        aVal = a.name;
        bVal = b.name;
      } else if (sortKey === 'age') {
        aVal = a.age;
        bVal = b.age;
      } else {
        aVal = a.email;
        bVal = b.email;
      }
      
      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });
    return sorted;
  }, [data, sortKey, sortOrder]);

  const { startIndex, endIndex, virtualHeight, offsetY } = useMemo(() => {
    const start = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
    const end = Math.min(
      sortedData.length,
      Math.ceil((scrollTop + VISIBLE_ROWS * ROW_HEIGHT) / ROW_HEIGHT) + OVERSCAN
    );
    return {
      startIndex: start,
      endIndex: end,
      virtualHeight: sortedData.length * ROW_HEIGHT,
      offsetY: start * ROW_HEIGHT,
    };
  }, [scrollTop, sortedData.length]);

  const visibleRows = useMemo(() => {
    return sortedData.slice(startIndex, endIndex);
  }, [sortedData, startIndex, endIndex]);

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  }, []);

  const handleSort = useCallback((key: SortKey) => {
    setSortKey(key);
    setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
  }, []);

  const getSortIndicator = (key: SortKey) => {
    if (sortKey !== key) return '↕';
    return sortOrder === 'asc' ? '↑' : '↓';
  };

  return (
    <div className={styles.container}>
      <h2>Virtual Scroll Table (10,000 rows)</h2>
      <div 
        ref={containerRef}
        className={styles.tableWrapper}
        onScroll={handleScroll}
        style={{ height: VISIBLE_ROWS * ROW_HEIGHT + ROW_HEIGHT }}
      >
        <table className={styles.table}>
          <thead className={styles.header}>
            <tr>
              <th>ID</th>
              <th onClick={() => handleSort('name')} className={styles.sortable}>
                Name {getSortIndicator('name')}
              </th>
              <th onClick={() => handleSort('age')} className={styles.sortable}>
                Age {getSortIndicator('age')}
              </th>
              <th onClick={() => handleSort('email')} className={styles.sortable}>
                Email {getSortIndicator('email')}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr style={{ height: offsetY }}>
              <td colSpan={4}></td>
            </tr>
            {visibleRows.map(row => (
              <tr key={row.id} className={styles.row} style={{ height: ROW_HEIGHT }}>
                <td>{row.id}</td>
                <td>{row.name}</td>
                <td>{row.age}</td>
                <td>{row.email}</td>
              </tr>
            ))}
            <tr style={{ height: virtualHeight - offsetY - visibleRows.length * ROW_HEIGHT }}>
              <td colSpan={4}></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* CSS Module - VirtualScrollTable.module.css
.container {
  padding: 20px;
  font-family: Arial, sans-serif;
}

.tableWrapper {
  overflow: auto;
  border: 1px solid #ddd;
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

.header th {
  padding: 10px;
  text-align: left;
  border-bottom: 2px solid #ddd;
  font-weight: bold;
}

.sortable {
  cursor: pointer;
  user-select: none;
}

.sortable:hover {
  background: #e0e0e0;
}

.row td {
  padding: 10px;
  border-bottom: 1px solid #eee;
}

.row:hover {
  background: #f9f9f9;
}
*/
