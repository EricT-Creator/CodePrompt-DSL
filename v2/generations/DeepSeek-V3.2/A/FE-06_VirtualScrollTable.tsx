import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';

interface TableData {
  id: number;
  name: string;
  age: number;
  email: string;
  city: string;
}

interface SortConfig {
  key: keyof TableData;
  direction: 'asc' | 'desc';
}

const VirtualScrollTable: React.FC = () => {
  const ROW_HEIGHT = 48;
  const VISIBLE_ROWS = 15;
  const OVERSCAN = 5;
  const TOTAL_ROWS = 10000;

  const [sortConfig, setSortConfig] = useState<SortConfig>({ key: 'id', direction: 'asc' });
  const [scrollTop, setScrollTop] = useState<number>(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const generateData = useCallback((start: number, end: number): TableData[] => {
    const data: TableData[] = [];
    for (let i = start; i <= end; i++) {
      data.push({
        id: i,
        name: `User ${i}`,
        age: 18 + (i % 50),
        email: `user${i}@example.com`,
        city: ['New York', 'London', 'Tokyo', 'Paris', 'Berlin'][i % 5],
      });
    }
    return data;
  }, []);

  const allData = useMemo(() => generateData(1, TOTAL_ROWS), [generateData]);

  const sortedData = useMemo(() => {
    const sortableData = [...allData];
    if (sortConfig.key) {
      sortableData.sort((a, b) => {
        const aValue = a[sortConfig.key];
        const bValue = b[sortConfig.key];
        
        if (aValue < bValue) {
          return sortConfig.direction === 'asc' ? -1 : 1;
        }
        if (aValue > bValue) {
          return sortConfig.direction === 'asc' ? 1 : -1;
        }
        return 0;
      });
    }
    return sortableData;
  }, [allData, sortConfig]);

  const handleScroll = useCallback(() => {
    if (containerRef.current) {
      setScrollTop(containerRef.current.scrollTop);
    }
  }, []);

  const requestSort = (key: keyof TableData) => {
    let direction: 'asc' | 'desc' = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const getSortIndicator = (key: keyof TableData) => {
    if (sortConfig.key !== key) return '';
    return sortConfig.direction === 'asc' ? ' ↑' : ' ↓';
  };

  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const endIndex = Math.min(
    sortedData.length - 1,
    startIndex + VISIBLE_ROWS + OVERSCAN * 2
  );

  const visibleRows = sortedData.slice(startIndex, endIndex + 1);

  const translateY = startIndex * ROW_HEIGHT;

  useEffect(() => {
    const container = containerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll);
      return () => container.removeEventListener('scroll', handleScroll);
    }
  }, [handleScroll]);

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Virtual Scroll Table (10,000 Rows)</h2>
      <div style={styles.tableInfo}>
        <div>Showing rows {startIndex + 1} - {endIndex + 1} of {TOTAL_ROWS}</div>
        <div style={styles.sortInfo}>
          Sorted by: {sortConfig.key} ({sortConfig.direction})
        </div>
      </div>
      
      <div 
        ref={containerRef}
        style={styles.tableContainer}
      >
        <div style={styles.tableWrapper}>
          <div style={styles.tableHeader}>
            <div 
              style={styles.headerCell}
              onClick={() => requestSort('id')}
            >
              ID{getSortIndicator('id')}
            </div>
            <div 
              style={styles.headerCell}
              onClick={() => requestSort('name')}
            >
              Name{getSortIndicator('name')}
            </div>
            <div 
              style={styles.headerCell}
              onClick={() => requestSort('age')}
            >
              Age{getSortIndicator('age')}
            </div>
            <div 
              style={styles.headerCell}
              onClick={() => requestSort('email')}
            >
              Email{getSortIndicator('email')}
            </div>
            <div 
              style={styles.headerCell}
              onClick={() => requestSort('city')}
            >
              City{getSortIndicator('city')}
            </div>
          </div>
          
          <div style={styles.tableBody}>
            <div style={{ height: sortedData.length * ROW_HEIGHT, position: 'relative' }}>
              <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                transform: `translateY(${translateY}px)`,
              }}>
                {visibleRows.map((row) => (
                  <div
                    key={row.id}
                    style={{
                      ...styles.row,
                      height: ROW_HEIGHT,
                      backgroundColor: row.id % 2 === 0 ? '#ffffff' : '#f8f9fa',
                    }}
                  >
                    <div style={styles.cell}>{row.id}</div>
                    <div style={styles.cell}>{row.name}</div>
                    <div style={styles.cell}>{row.age}</div>
                    <div style={styles.cell}>{row.email}</div>
                    <div style={styles.cell}>{row.city}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div style={styles.footer}>
        <div style={styles.stats}>
          <div>Total Rows: {TOTAL_ROWS.toLocaleString()}</div>
          <div>Visible Rows: {visibleRows.length}</div>
          <div>Scroll Position: {Math.round(scrollTop)}px</div>
        </div>
        <div style={styles.note}>
          Virtual scrolling with {OVERSCAN} row overscan buffer. Only {VISIBLE_ROWS} rows are rendered at a time.
        </div>
      </div>
    </div>
  );
};

const styles = {
  container: {
    fontFamily: 'Arial, sans-serif',
    maxWidth: '1000px',
    margin: '0 auto',
    padding: '20px',
  },
  title: {
    textAlign: 'center' as const,
    color: '#333',
    marginBottom: '20px',
  },
  tableInfo: {
    display: 'flex' as const,
    justifyContent: 'space-between' as const,
    alignItems: 'center' as const,
    marginBottom: '15px',
    padding: '10px',
    backgroundColor: '#f5f5f5',
    borderRadius: '4px',
    fontSize: '14px',
  },
  sortInfo: {
    backgroundColor: '#e3f2fd',
    padding: '4px 8px',
    borderRadius: '4px',
    color: '#1976d2',
  },
  tableContainer: {
    height: `${15 * 48 + 48}px`,
    overflowY: 'auto' as const,
    border: '1px solid #ddd',
    borderRadius: '8px',
    backgroundColor: '#fff',
  },
  tableWrapper: {
    position: 'relative' as const,
  },
  tableHeader: {
    position: 'sticky' as const,
    top: 0,
    display: 'flex' as const,
    backgroundColor: '#f1f3f4',
    borderBottom: '2px solid #ddd',
    zIndex: 10,
  },
  headerCell: {
    flex: 1,
    padding: '16px',
    fontWeight: 'bold' as const,
    cursor: 'pointer' as const,
    userSelect: 'none' as const,
    borderRight: '1px solid #ddd',
    minWidth: '0',
    overflow: 'hidden',
    textOverflow: 'ellipsis' as const,
    whiteSpace: 'nowrap' as const,
    transition: 'background-color 0.2s',
  },
  tableBody: {
    position: 'relative' as const,
  },
  row: {
    display: 'flex' as const,
    borderBottom: '1px solid #eee',
    transition: 'background-color 0.2s',
  },
  cell: {
    flex: 1,
    padding: '12px 16px',
    borderRight: '1px solid #eee',
    minWidth: '0',
    overflow: 'hidden',
    textOverflow: 'ellipsis' as const,
    whiteSpace: 'nowrap' as const,
  },
  footer: {
    marginTop: '20px',
    padding: '15px',
    backgroundColor: '#f9f9f9',
    borderRadius: '8px',
    fontSize: '14px',
  },
  stats: {
    display: 'flex' as const,
    justifyContent: 'space-between' as const,
    marginBottom: '10px',
  },
  note: {
    color: '#666',
    fontSize: '12px',
    textAlign: 'center' as const,
  },
};

export default VirtualScrollTable;

/*
// VirtualScrollTable.module.css

.container {
  font-family: Arial, sans-serif;
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
}

.title {
  text-align: center;
  color: #333;
  margin-bottom: 20px;
}

.tableInfo {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding: 10px;
  background-color: #f5f5f5;
  border-radius: 4px;
  font-size: 14px;
}

.sortInfo {
  background-color: #e3f2fd;
  padding: 4px 8px;
  border-radius: 4px;
  color: #1976d2;
}

.tableContainer {
  height: 768px; /* 15 rows * 48px + header */
  overflow-y: auto;
  border: 1px solid #ddd;
  border-radius: 8px;
  background-color: #fff;
}

.tableWrapper {
  position: relative;
}

.tableHeader {
  position: sticky;
  top: 0;
  display: flex;
  background-color: #f1f3f4;
  border-bottom: 2px solid #ddd;
  z-index: 10;
}

.headerCell {
  flex: 1;
  padding: 16px;
  font-weight: bold;
  cursor: pointer;
  user-select: none;
  border-right: 1px solid #ddd;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: background-color 0.2s;
}

.headerCell:hover {
  background-color: #e0e0e0;
}

.tableBody {
  position: relative;
}

.row {
  display: flex;
  border-bottom: 1px solid #eee;
  transition: background-color 0.2s;
}

.row:hover {
  background-color: #f0f7ff;
}

.cell {
  flex: 1;
  padding: 12px 16px;
  border-right: 1px solid #eee;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.footer {
  margin-top: 20px;
  padding: 15px;
  background-color: #f9f9f9;
  border-radius: 8px;
  font-size: 14px;
}

.stats {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}

.note {
  color: #666;
  font-size: 12px;
  text-align: center;
}
*/