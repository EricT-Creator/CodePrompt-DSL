import React, { useState, useMemo, useRef, useEffect } from 'react';
import styles from './styles.module.css';

interface RowData {
  id: number;
  name: string;
  email: string;
  age: number;
  city: string;
  score: number;
}

type SortDirection = 'asc' | 'desc' | null;

interface SortConfig {
  column: keyof RowData | null;
  direction: SortDirection;
}

const ROW_HEIGHT = 36;
const VIEWPORT_HEIGHT = 600;
const OVERSCAN = 5;

const generateMockData = (count: number): RowData[] => {
  const cities = ['New York', 'London', 'Tokyo', 'Paris', 'Berlin', 'Sydney', 'Toronto', 'Singapore'];
  return Array.from({ length: count }, (_, i) => ({
    id: i,
    name: `User ${i}`,
    email: `user${i}@example.com`,
    age: Math.floor(Math.random() * 50) + 18,
    city: cities[Math.floor(Math.random() * cities.length)],
    score: Math.floor(Math.random() * 1000),
  }));
};

const FilterBar: React.FC<{
  filter: string;
  onFilterChange: (value: string) => void;
}> = ({ filter, onFilterChange }) => {
  return (
    <div className={styles.filterBar}>
      <input
        type="text"
        value={filter}
        onChange={(e) => onFilterChange(e.target.value)}
        placeholder="Filter by name or email..."
        className={styles.filterInput}
      />
    </div>
  );
};

const GridHeader: React.FC<{
  columns: Array<{ key: keyof RowData; label: string }>;
  sortConfig: SortConfig;
  onSort: (column: keyof RowData) => void;
}> = ({ columns, sortConfig, onSort }) => {
  const getSortIndicator = (column: keyof RowData) => {
    if (sortConfig.column !== column) return null;
    return sortConfig.direction === 'asc' ? '↑' : sortConfig.direction === 'desc' ? '↓' : null;
  };

  return (
    <div className={styles.gridHeader}>
      {columns.map(col => (
        <div
          key={col.key}
          className={`${styles.headerCell} ${
            sortConfig.column === col.key ? styles.sorted : ''
          }`}
          onClick={() => onSort(col.key)}
        >
          <span>{col.label}</span>
          {getSortIndicator(col.key) && (
            <span className={styles.sortIndicator}>{getSortIndicator(col.key)}</span>
          )}
        </div>
      ))}
    </div>
  );
};

const GridRow: React.FC<{
  row: RowData;
  style: React.CSSProperties;
}> = ({ row, style }) => {
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
};

const VirtualBody: React.FC<{
  data: RowData[];
  scrollTop: number;
  onScroll: (scrollTop: number) => void;
}> = ({ data, scrollTop, onScroll }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const scrollTimerRef = useRef<number | null>(null);

  const totalRows = data.length;
  const totalHeight = totalRows * ROW_HEIGHT;

  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const endIndex = Math.min(
    totalRows - 1,
    Math.ceil((scrollTop + VIEWPORT_HEIGHT) / ROW_HEIGHT) + OVERSCAN
  );

  const visibleRows = data.slice(startIndex, endIndex + 1);

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const newScrollTop = e.currentTarget.scrollTop;
    
    if (scrollTimerRef.current) {
      cancelAnimationFrame(scrollTimerRef.current);
    }
    
    scrollTimerRef.current = requestAnimationFrame(() => {
      onScroll(newScrollTop);
    });
  };

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = scrollTop;
    }
  }, []);

  return (
    <div
      ref={containerRef}
      className={styles.virtualBody}
      style={{ height: VIEWPORT_HEIGHT }}
      onScroll={handleScroll}
    >
      <div
        className={styles.spacer}
        style={{ height: totalHeight }}
      />
      {visibleRows.map((row, index) => (
        <GridRow
          key={row.id}
          row={row}
          style={{
            position: 'absolute',
            top: (startIndex + index) * ROW_HEIGHT,
            height: ROW_HEIGHT,
            width: '100%',
          }}
        />
      ))}
    </div>
  );
};

const DataGrid: React.FC = () => {
  const [filter, setFilter] = useState('');
  const [sortConfig, setSortConfig] = useState<SortConfig>({ column: null, direction: null });
  const [scrollTop, setScrollTop] = useState(0);

  const dataRef = useRef<RowData[]>(generateMockData(10000));

  const columns: Array<{ key: keyof RowData; label: string }> = [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Name' },
    { key: 'email', label: 'Email' },
    { key: 'age', label: 'Age' },
    { key: 'city', label: 'City' },
    { key: 'score', label: 'Score' },
  ];

  const filteredData = useMemo(() => {
    if (!filter.trim()) return dataRef.current;
    
    const lowerFilter = filter.toLowerCase();
    return dataRef.current.filter(row =>
      row.name.toLowerCase().includes(lowerFilter) ||
      row.email.toLowerCase().includes(lowerFilter)
    );
  }, [filter]);

  const sortedData = useMemo(() => {
    if (!sortConfig.column || !sortConfig.direction) return filteredData;
    
    return [...filteredData].sort((a, b) => {
      const aVal = a[sortConfig.column!];
      const bVal = b[sortConfig.column!];
      
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortConfig.direction === 'asc'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }
      
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortConfig.direction === 'asc'
          ? aVal - bVal
          : bVal - aVal;
      }
      
      return 0;
    });
  }, [filteredData, sortConfig]);

  const handleSort = (column: keyof RowData) => {
    setSortConfig(prev => {
      if (prev.column !== column) {
        return { column, direction: 'asc' };
      }
      
      if (prev.direction === 'asc') {
        return { column, direction: 'desc' };
      }
      
      if (prev.direction === 'desc') {
        return { column: null, direction: null };
      }
      
      return { column, direction: 'asc' };
    });
  };

  return (
    <div className={styles.dataGrid}>
      <div className={styles.header}>
        <h1>Virtual Scroll Data Grid</h1>
        <div className={styles.stats}>
          {sortedData.length.toLocaleString()} rows
        </div>
      </div>
      
      <FilterBar
        filter={filter}
        onFilterChange={setFilter}
      />
      
      <div className={styles.gridContainer}>
        <GridHeader
          columns={columns}
          sortConfig={sortConfig}
          onSort={handleSort}
        />
        
        <VirtualBody
          data={sortedData}
          scrollTop={scrollTop}
          onScroll={setScrollTop}
        />
      </div>
      
      <div className={styles.footer}>
        <div className={styles.scrollInfo}>
          Scroll position: {Math.round(scrollTop)}px
        </div>
        <div className={styles.visibleInfo}>
          Visible rows: {Math.floor(scrollTop / ROW_HEIGHT)} - {Math.ceil((scrollTop + VIEWPORT_HEIGHT) / ROW_HEIGHT)}
        </div>
      </div>
    </div>
  );
};

export default DataGrid;