import React, { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import styles from './DataGrid.module.css';

interface DataRow {
  id: number;
  name: string;
  email: string;
  department: string;
  salary: number;
  joinDate: string;
}

interface ColumnDef {
  key: keyof DataRow;
  label: string;
  width: number;
  sortable: boolean;
}

type SortDirection = 'asc' | 'desc' | null;

interface SortState {
  column: keyof DataRow | null;
  direction: SortDirection;
}

const ROW_HEIGHT = 36;
const OVERSCAN = 5;
const CONTAINER_HEIGHT = 400;

const COLUMNS: ColumnDef[] = [
  { key: 'id', label: 'ID', width: 80, sortable: true },
  { key: 'name', label: 'Name', width: 150, sortable: true },
  { key: 'email', label: 'Email', width: 200, sortable: true },
  { key: 'department', label: 'Department', width: 120, sortable: true },
  { key: 'salary', label: 'Salary', width: 100, sortable: true },
  { key: 'joinDate', label: 'Join Date', width: 120, sortable: true },
];

function generateMockData(count: number): DataRow[] {
  const departments = ['Engineering', 'Sales', 'Marketing', 'HR', 'Finance', 'Operations'];
  const data: DataRow[] = [];
  
  for (let i = 0; i < count; i++) {
    data.push({
      id: i + 1,
      name: `User_${i}`,
      email: `user_${i}@company.com`,
      department: departments[i % departments.length],
      salary: 30000 + ((i * 7) % 70000),
      joinDate: new Date(2020 + (i % 5), (i % 12), 1 + (i % 28)).toISOString().split('T')[0],
    });
  }
  
  return data;
}

const MOCK_DATA = generateMockData(10000);

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);
  
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  
  return debouncedValue;
}

export default function DataGrid() {
  const [filterText, setFilterText] = useState('');
  const [sort, setSort] = useState<SortState>({ column: null, direction: null });
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number | null>(null);
  
  const debouncedFilter = useDebounce(filterText, 150);
  
  const filteredData = useMemo(() => {
    if (!debouncedFilter) return MOCK_DATA;
    const lowerFilter = debouncedFilter.toLowerCase();
    return MOCK_DATA.filter(row => 
      row.name.toLowerCase().includes(lowerFilter) ||
      row.email.toLowerCase().includes(lowerFilter)
    );
  }, [debouncedFilter]);
  
  const sortedData = useMemo(() => {
    if (!sort.column || !sort.direction) return filteredData;
    
    return [...filteredData].sort((a, b) => {
      const aVal = a[sort.column!];
      const bVal = b[sort.column!];
      
      let comparison = 0;
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        comparison = aVal - bVal;
      } else if (sort.column === 'joinDate') {
        comparison = new Date(aVal as string).getTime() - new Date(bVal as string).getTime();
      } else {
        comparison = String(aVal).localeCompare(String(bVal));
      }
      
      return sort.direction === 'asc' ? comparison : -comparison;
    });
  }, [filteredData, sort]);
  
  const totalHeight = sortedData.length * ROW_HEIGHT;
  
  const { startIndex, endIndex, visibleRows } = useMemo(() => {
    const start = Math.floor(scrollTop / ROW_HEIGHT);
    const end = Math.min(
      start + Math.ceil(CONTAINER_HEIGHT / ROW_HEIGHT) + OVERSCAN,
      sortedData.length - 1
    );
    const visible = sortedData.slice(start, end + 1);
    return { startIndex: start, endIndex: end, visibleRows: visible };
  }, [scrollTop, sortedData]);
  
  const spacerTopHeight = startIndex * ROW_HEIGHT;
  const spacerBottomHeight = (sortedData.length - endIndex - 1) * ROW_HEIGHT;
  
  const handleScroll = useCallback(() => {
    if (rafRef.current) return;
    
    rafRef.current = requestAnimationFrame(() => {
      if (containerRef.current) {
        setScrollTop(containerRef.current.scrollTop);
      }
      rafRef.current = null;
    });
  }, []);
  
  const handleSort = useCallback((column: keyof DataRow) => {
    const colDef = COLUMNS.find(c => c.key === column);
    if (!colDef?.sortable) return;
    
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
  
  const getSortIndicator = (column: keyof DataRow) => {
    if (sort.column !== column) return null;
    return sort.direction === 'asc' ? ' ▲' : ' ▼';
  };
  
  return (
    <div className={styles.grid}>
      <div className={styles.searchBar}>
        <input
          type="text"
          value={filterText}
          onChange={(e) => setFilterText(e.target.value)}
          placeholder="Search by name or email..."
          className={styles.searchInput}
        />
        <span className={styles.rowCount}>{sortedData.length.toLocaleString()} rows</span>
      </div>
      
      <div className={styles.header}>
        {COLUMNS.map(col => (
          <div
            key={String(col.key)}
            className={`${styles.headerCell} ${col.sortable ? styles.sortable : ''}`}
            style={{ width: col.width }}
            onClick={() => handleSort(col.key)}
          >
            {col.label}{getSortIndicator(col.key)}
          </div>
        ))}
      </div>
      
      <div
        ref={containerRef}
        className={styles.virtualBody}
        onScroll={handleScroll}
      >
        <div style={{ height: totalHeight, position: 'relative' }}>
          <div style={{ height: spacerTopHeight }} />
          
          {visibleRows.map((row, index) => (
            <div
              key={row.id}
              className={styles.row}
              style={{
                height: ROW_HEIGHT,
                willChange: 'transform',
              }}
            >
              {COLUMNS.map(col => (
                <div
                  key={String(col.key)}
                  className={styles.cell}
                  style={{ width: col.width }}
                >
                  {col.key === 'salary' 
                    ? `$${(row[col.key] as number).toLocaleString()}`
                    : String(row[col.key])
                  }
                </div>
              ))}
            </div>
          ))}
          
          <div style={{ height: spacerBottomHeight }} />
        </div>
      </div>
    </div>
  );
}
