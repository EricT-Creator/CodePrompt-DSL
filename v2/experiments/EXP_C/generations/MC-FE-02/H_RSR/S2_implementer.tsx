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

interface GridState {
  data: DataRow[];
  filterText: string;
  sort: SortState;
  scrollTop: number;
}

const ROW_HEIGHT = 36;
const OVERSCAN = 5;
const CONTAINER_HEIGHT = 600;

function generateMockData(count: number): DataRow[] {
  const departments = ['Engineering', 'Marketing', 'Sales', 'HR', 'Finance', 'Operations'];
  const firstNames = ['Alex', 'Jamie', 'Taylor', 'Morgan', 'Casey', 'Jordan', 'Riley', 'Quinn'];
  const lastNames = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis'];
  
  const data: DataRow[] = [];
  
  for (let i = 0; i < count; i++) {
    const firstName = firstNames[Math.floor(Math.random() * firstNames.length)];
    const lastName = lastNames[Math.floor(Math.random() * lastNames.length)];
    const department = departments[Math.floor(Math.random() * departments.length)];
    
    data.push({
      id: i + 1,
      name: `${firstName} ${lastName}`,
      email: `${firstName.toLowerCase()}.${lastName.toLowerCase()}@company.com`,
      department,
      salary: 30000 + (i * 7) % 70000,
      joinDate: `202${Math.floor(Math.random() * 6)}-${String(Math.floor(Math.random() * 12) + 1).padStart(2, '0')}-${String(Math.floor(Math.random() * 28) + 1).padStart(2, '0')}`
    });
  }
  
  return data;
}

const columns: ColumnDef[] = [
  { key: 'id', label: 'ID', width: 80, sortable: true },
  { key: 'name', label: 'Name', width: 200, sortable: true },
  { key: 'email', label: 'Email', width: 250, sortable: true },
  { key: 'department', label: 'Department', width: 150, sortable: true },
  { key: 'salary', label: 'Salary', width: 120, sortable: true },
  { key: 'joinDate', label: 'Join Date', width: 120, sortable: true }
];

const SearchBar: React.FC<{
  filterText: string;
  onFilterChange: (text: string) => void;
}> = ({ filterText, onFilterChange }) => {
  const [localText, setLocalText] = useState(filterText);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setLocalText(value);
    
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    
    timeoutRef.current = setTimeout(() => {
      onFilterChange(value);
    }, 150);
  }, [onFilterChange]);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return (
    <div className={styles.searchBar}>
      <input
        type="text"
        className={styles.searchInput}
        placeholder="Search by name or email..."
        value={localText}
        onChange={handleChange}
      />
      <span className={styles.searchIcon}>🔍</span>
    </div>
  );
};

const GridHeader: React.FC<{
  columns: ColumnDef[];
  sort: SortState;
  onSortChange: (column: keyof DataRow) => void;
}> = ({ columns, sort, onSortChange }) => {
  const getSortIcon = (columnKey: keyof DataRow) => {
    if (sort.column !== columnKey) return '↕️';
    return sort.direction === 'asc' ? '↑' : '↓';
  };

  return (
    <div className={styles.gridHeader}>
      {columns.map((col) => (
        <div
          key={col.key}
          className={`${styles.headerCell} ${col.sortable ? styles.sortable : ''}`}
          style={{ width: col.width }}
          onClick={() => col.sortable && onSortChange(col.key)}
        >
          <span className={styles.headerLabel}>{col.label}</span>
          {col.sortable && (
            <span className={styles.sortIcon}>
              {getSortIcon(col.key)}
            </span>
          )}
        </div>
      ))}
    </div>
  );
};

const GridRow: React.FC<{
  row: DataRow;
  columns: ColumnDef[];
}> = ({ row, columns }) => {
  return (
    <div className={styles.gridRow}>
      {columns.map((col) => (
        <div
          key={col.key}
          className={styles.cell}
          style={{ width: col.width }}
          title={String(row[col.key])}
        >
          {col.key === 'salary' ? `$${row[col.key].toLocaleString()}` : row[col.key]}
        </div>
      ))}
    </div>
  );
};

const VirtualBody: React.FC<{
  data: DataRow[];
  columns: ColumnDef[];
  scrollTop: number;
  onScroll: (scrollTop: number) => void;
}> = ({ data, columns, scrollTop, onScroll }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number | null>(null);

  const totalRows = data.length;
  const startIndex = Math.floor(scrollTop / ROW_HEIGHT);
  const visibleRowCount = Math.ceil(CONTAINER_HEIGHT / ROW_HEIGHT);
  const endIndex = Math.min(
    startIndex + visibleRowCount + OVERSCAN * 2,
    totalRows - 1
  );

  const visibleRows = data.slice(startIndex, endIndex + 1);

  const spacerTopHeight = startIndex * ROW_HEIGHT;
  const spacerBottomHeight = Math.max(0, (totalRows - endIndex - 1) * ROW_HEIGHT);

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
    }

    rafRef.current = requestAnimationFrame(() => {
      const newScrollTop = e.currentTarget.scrollTop;
      onScroll(newScrollTop);
    });
  }, [onScroll]);

  useEffect(() => {
    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className={styles.virtualBody}
      style={{ height: CONTAINER_HEIGHT }}
      onScroll={handleScroll}
    >
      <div
        className={styles.scrollContent}
        style={{ height: totalRows * ROW_HEIGHT }}
      >
        <div
          className={styles.spacer}
          style={{ height: spacerTopHeight }}
        />
        
        {visibleRows.map((row, index) => (
          <div
            key={row.id}
            className={styles.rowContainer}
            style={{
              position: 'absolute',
              top: (startIndex + index) * ROW_HEIGHT,
              height: ROW_HEIGHT,
              width: '100%'
            }}
          >
            <GridRow row={row} columns={columns} />
          </div>
        ))}
        
        <div
          className={styles.spacer}
          style={{ height: spacerBottomHeight }}
        />
      </div>
    </div>
  );
};

const DataGrid: React.FC = () => {
  const [state, setState] = useState<GridState>({
    data: generateMockData(10000),
    filterText: '',
    sort: { column: null, direction: null },
    scrollTop: 0
  });

  const filteredData = useMemo(() => {
    const { data, filterText } = state;
    if (!filterText.trim()) return data;
    
    const searchText = filterText.toLowerCase();
    return data.filter(row => 
      row.name.toLowerCase().includes(searchText) ||
      row.email.toLowerCase().includes(searchText)
    );
  }, [state.data, state.filterText]);

  const sortedData = useMemo(() => {
    const { sort } = state;
    if (!sort.column || !sort.direction) return filteredData;
    
    return [...filteredData].sort((a, b) => {
      const aVal = a[sort.column!];
      const bVal = b[sort.column!];
      
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sort.direction === 'asc' ? aVal - bVal : bVal - aVal;
      }
      
      if (sort.column === 'joinDate') {
        const dateA = new Date(aVal as string);
        const dateB = new Date(bVal as string);
        return sort.direction === 'asc' ? dateA.getTime() - dateB.getTime() : dateB.getTime() - dateA.getTime();
      }
      
      const strA = String(aVal);
      const strB = String(bVal);
      return sort.direction === 'asc' 
        ? strA.localeCompare(strB)
        : strB.localeCompare(strA);
    });
  }, [filteredData, state.sort]);

  const handleFilterChange = useCallback((text: string) => {
    setState(prev => ({ ...prev, filterText: text, scrollTop: 0 }));
  }, []);

  const handleSortChange = useCallback((column: keyof DataRow) => {
    setState(prev => {
      let direction: SortDirection;
      
      if (prev.sort.column !== column) {
        direction = 'asc';
      } else if (prev.sort.direction === 'asc') {
        direction = 'desc';
      } else if (prev.sort.direction === 'desc') {
        direction = null;
      } else {
        direction = 'asc';
      }
      
      return {
        ...prev,
        sort: {
          column: direction ? column : null,
          direction
        }
      };
    });
  }, []);

  const handleScroll = useCallback((scrollTop: number) => {
    setState(prev => ({ ...prev, scrollTop }));
  }, []);

  return (
    <div className={styles.dataGrid}>
      <div className={styles.gridHeaderContainer}>
        <div className={styles.stats}>
          <span className={styles.totalRows}>
            Total: {sortedData.length.toLocaleString()} rows
          </span>
          {state.filterText && (
            <span className={styles.filteredRows}>
              Filtered: {sortedData.length.toLocaleString()} rows
            </span>
          )}
        </div>
        <SearchBar
          filterText={state.filterText}
          onFilterChange={handleFilterChange}
        />
      </div>
      
      <GridHeader
        columns={columns}
        sort={state.sort}
        onSortChange={handleSortChange}
      />
      
      <VirtualBody
        data={sortedData}
        columns={columns}
        scrollTop={state.scrollTop}
        onScroll={handleScroll}
      />
      
      <div className={styles.gridFooter}>
        <div className={styles.scrollInfo}>
          <span>Scroll position: {Math.floor(state.scrollTop).toLocaleString()}px</span>
          <span>Visible rows: {Math.ceil(CONTAINER_HEIGHT / ROW_HEIGHT)}</span>
          <span>Overscan: {OVERSCAN * 2} rows</span>
        </div>
      </div>
    </div>
  );
};

export default DataGrid;