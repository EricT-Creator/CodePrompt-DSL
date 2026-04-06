import React, { useState, useMemo, useRef, useCallback } from 'react';
import styles from './S2_implementer.module.css';

interface RowData {
  id: number;
  name: string;
  email: string;
  age: number;
  city: string;
  score: number;
}

interface SortConfig {
  column: keyof RowData | null;
  direction: 'asc' | 'desc' | null;
}

const ROW_HEIGHT = 36;
const VIEWPORT_HEIGHT = 600;
const OVERSCAN = 5;

function generateMockData(): RowData[] {
  return Array.from({ length: 10000 }, (_, i) => ({
    id: i,
    name: `User ${i}`,
    email: `user${i}@example.com`,
    age: 18 + (i % 50),
    city: ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix'][i % 5],
    score: Math.floor(Math.random() * 100),
  }));
}

const GridRow = React.memo<{ row: RowData; style: React.CSSProperties }>(({ row, style }) => {
  return (
    <div className={styles.gridRow} style={style}>
      <div className={styles.cell}>{row.id}</div>
      <div className={styles.cell}>{row.name}</div>
      <div className={styles.cell}>{row.email}</div>
      <div className={styles.cell}>{row.age}</div>
      <div className={styles.cell}>{row.city}</div>
      <div className={styles.cell}>{row.score}</div>
    </div>
  );
});

const DataGrid: React.FC = () => {
  const dataRef = useRef<RowData[]>(generateMockData());
  const [filter, setFilter] = useState('');
  const [sort, setSort] = useState<SortConfig>({ column: null, direction: null });
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const filteredData = useMemo(() => {
    if (!filter) return dataRef.current;
    const lowerFilter = filter.toLowerCase();
    return dataRef.current.filter(
      row =>
        row.name.toLowerCase().includes(lowerFilter) ||
        row.email.toLowerCase().includes(lowerFilter)
    );
  }, [filter]);

  const sortedData = useMemo(() => {
    if (!sort.column || !sort.direction) return filteredData;
    const sorted = [...filteredData];
    sorted.sort((a, b) => {
      const aVal = a[sort.column!];
      const bVal = b[sort.column!];
      if (typeof aVal === 'string') {
        return sort.direction === 'asc'
          ? aVal.localeCompare(bVal as string)
          : (bVal as string).localeCompare(aVal);
      }
      return sort.direction === 'asc'
        ? (aVal as number) - (bVal as number)
        : (bVal as number) - (aVal as number);
    });
    return sorted;
  }, [filteredData, sort]);

  const totalRows = sortedData.length;
  const totalHeight = totalRows * ROW_HEIGHT;

  const { startIndex, endIndex, visibleRows } = useMemo(() => {
    const start = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
    const end = Math.min(totalRows - 1, Math.ceil((scrollTop + VIEWPORT_HEIGHT) / ROW_HEIGHT) + OVERSCAN);
    return {
      startIndex: start,
      endIndex: end,
      visibleRows: sortedData.slice(start, end + 1),
    };
  }, [scrollTop, sortedData, totalRows]);

  const handleScroll = useCallback(() => {
    if (containerRef.current) {
      setScrollTop(containerRef.current.scrollTop);
    }
  }, []);

  const handleSort = useCallback((column: keyof RowData) => {
    setSort(prev => {
      if (prev.column !== column) {
        return { column, direction: 'asc' };
      }
      if (prev.direction === 'asc') {
        return { column, direction: 'desc' };
      }
      return { column: null, direction: null };
    });
  }, []);

  const columns: { key: keyof RowData; label: string }[] = [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Name' },
    { key: 'email', label: 'Email' },
    { key: 'age', label: 'Age' },
    { key: 'city', label: 'City' },
    { key: 'score', label: 'Score' },
  ];

  return (
    <div className={styles.dataGrid}>
      <div className={styles.filterBar}>
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter by name or email..."
        />
      </div>
      <div className={styles.gridHeader}>
        {columns.map(col => (
          <div
            key={col.key}
            className={styles.headerCell}
            onClick={() => handleSort(col.key)}
          >
            {col.label}
            {sort.column === col.key && (sort.direction === 'asc' ? ' ↑' : ' ↓')}
          </div>
        ))}
      </div>
      <div
        ref={containerRef}
        className={styles.virtualBody}
        onScroll={handleScroll}
        style={{ height: VIEWPORT_HEIGHT, overflow: 'auto' }}
      >
        <div style={{ height: totalHeight, position: 'relative' }}>
          {visibleRows.map((row, idx) => {
            const actualIndex = startIndex + idx;
            return (
              <GridRow
                key={row.id}
                row={row}
                style={{
                  position: 'absolute',
                  top: actualIndex * ROW_HEIGHT,
                  height: ROW_HEIGHT,
                  willChange: 'transform',
                }}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default DataGrid;
