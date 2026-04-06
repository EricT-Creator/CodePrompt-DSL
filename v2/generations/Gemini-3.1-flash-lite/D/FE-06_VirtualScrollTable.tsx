import React, { useState, useMemo, useRef, useEffect } from 'react';
import styles from './VirtualScrollTable.module.css';

const ROW_HEIGHT = 40;
const BUFFER_COUNT = 5;

const VirtualScrollTable: React.FC = () => {
  const [data] = useState(() => Array.from({ length: 10000 }, (_, i) => ({
    id: i,
    name: `Name ${i}`,
    age: Math.floor(Math.random() * 100),
    email: `email${i}@example.com`,
  })));

  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [containerHeight, setContainerHeight] = useState(600);
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' } | null>(null);

  const sortedData = useMemo(() => {
    if (!sortConfig) return data;
    const sorted = [...data];
    sorted.sort((a, b) => {
      const aVal = a[sortConfig.key as keyof typeof a];
      const bVal = b[sortConfig.key as keyof typeof b];
      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
    return sorted;
  }, [data, sortConfig]);

  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - BUFFER_COUNT);
  const endIndex = Math.min(
    sortedData.length,
    Math.ceil((scrollTop + containerHeight) / ROW_HEIGHT) + BUFFER_COUNT
  );

  const visibleData = sortedData.slice(startIndex, endIndex);

  const handleSort = (key: string) => {
    setSortConfig(prev => ({
      key,
      direction: prev?.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  return (
    <div
      ref={containerRef}
      className={styles.container}
      style={{ height: containerHeight, overflowY: 'auto' }}
      onScroll={(e) => setScrollTop(e.currentTarget.scrollTop)}
    >
      <table className={styles.table}>
        <thead>
          <tr>
            <th onClick={() => handleSort('id')}>ID</th>
            <th onClick={() => handleSort('name')}>Name</th>
            <th onClick={() => handleSort('age')}>Age</th>
          </tr>
        </thead>
        <tbody style={{ height: sortedData.length * ROW_HEIGHT, position: 'relative' }}>
          {visibleData.map((row, i) => (
            <tr
              key={row.id}
              style={{
                position: 'absolute',
                top: (startIndex + i) * ROW_HEIGHT,
                height: ROW_HEIGHT,
                width: '100%',
              }}
            >
              <td>{row.id}</td>
              <td>{row.name}</td>
              <td>{row.age}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default VirtualScrollTable;

/* 
.container { position: relative; }
.table { width: 100%; border-collapse: collapse; }
.table th, .table td { border: 1px solid #ccc; padding: 8px; }
*/
