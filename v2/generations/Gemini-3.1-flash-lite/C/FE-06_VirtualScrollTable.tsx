import React, { useState, useMemo, useRef, UIEvent } from 'react';
import styles from './VirtualScrollTable.module.css';

interface RowData {
  id: number;
  name: string;
  age: number;
  score: number;
}

const ROW_HEIGHT = 40;
const OVERSCAN = 5;

const VirtualScrollTable: React.FC = () => {
  const [data] = useState<RowData[]>(
    Array.from({ length: 10000 }, (_, i) => ({
      id: i,
      name: `Name ${i}`,
      age: Math.floor(Math.random() * 80) + 20,
      score: Math.floor(Math.random() * 100),
    }))
  );

  const [sortBy, setSortBy] = useState<keyof RowData>('id');
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const sortedData = useMemo(() => {
    return [...data].sort((a, b) => (a[sortBy] > b[sortBy] ? 1 : -1));
  }, [data, sortBy]);

  const onScroll = (e: UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  };

  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const endIndex = Math.min(
    sortedData.length - 1,
    Math.ceil((scrollTop + (containerRef.current?.clientHeight || 0)) / ROW_HEIGHT) + OVERSCAN
  );

  const visibleRows = sortedData.slice(startIndex, endIndex + 1);

  return (
    <div className={styles.container} ref={containerRef} onScroll={onScroll}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th onClick={() => setSortBy('id')}>ID</th>
            <th onClick={() => setSortBy('name')}>Name</th>
            <th onClick={() => setSortBy('age')}>Age</th>
            <th onClick={() => setSortBy('score')}>Score</th>
          </tr>
        </thead>
        <tbody style={{ height: sortedData.length * ROW_HEIGHT }}>
          {visibleRows.map((row, i) => (
            <tr
              key={row.id}
              style={{
                position: 'absolute',
                top: (startIndex + i) * ROW_HEIGHT,
                width: '100%',
                height: ROW_HEIGHT,
              }}
            >
              <td>{row.id}</td>
              <td>{row.name}</td>
              <td>{row.age}</td>
              <td>{row.score}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default VirtualScrollTable;

/* 
.container {
  height: 400px;
  overflow: auto;
  position: relative;
}
.table {
  width: 100%;
  border-collapse: collapse;
}
*/