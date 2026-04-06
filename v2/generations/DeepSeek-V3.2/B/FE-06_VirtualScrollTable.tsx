import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';

interface RowData {
  id: number;
  name: string;
  email: string;
  age: number;
}

const generateData = (count: number): RowData[] => {
  const data: RowData[] = [];
  for (let i = 1; i <= count; i++) {
    data.push({
      id: i,
      name: `User ${i}`,
      email: `user${i}@example.com`,
      age: Math.floor(Math.random() * 50) + 20,
    });
  }
  return data;
};

const VirtualScrollTable: React.FC = () => {
  const [data] = useState<RowData[]>(() => generateData(10000));
  const [sortConfig, setSortConfig] = useState<{ key: keyof RowData; direction: 'asc' | 'desc' } | null>(null);
  const [scrollTop, setScrollTop] = useState<number>(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const tableRef = useRef<HTMLTableElement>(null);
  
  const rowHeight = 40;
  const headerHeight = 50;
  const visibleRows = 20;
  const overscan = 5;
  
  const sortedData = useMemo(() => {
    if (!sortConfig) return data;
    
    return [...data].sort((a, b) => {
      const aValue = a[sortConfig.key];
      const bValue = b[sortConfig.key];
      
      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortConfig.direction === 'asc'
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }
      
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortConfig.direction === 'asc'
          ? aValue - bValue
          : bValue - aValue;
      }
      
      return 0;
    });
  }, [data, sortConfig]);
  
  const totalHeight = data.length * rowHeight + headerHeight;
  
  const startIndex = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan);
  const endIndex = Math.min(data.length, startIndex + visibleRows + overscan * 2);
  
  const visibleData = sortedData.slice(startIndex, endIndex);
  
  const handleSort = (key: keyof RowData) => {
    setSortConfig(current => {
      if (!current || current.key !== key) {
        return { key, direction: 'asc' };
      }
      if (current.direction === 'asc') {
        return { key, direction: 'desc' };
      }
      return null;
    });
  };
  
  const handleScroll = useCallback(() => {
    if (containerRef.current) {
      setScrollTop(containerRef.current.scrollTop);
    }
  }, []);
  
  useEffect(() => {
    const container = containerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll);
      return () => container.removeEventListener('scroll', handleScroll);
    }
  }, [handleScroll]);
  
  const getSortIndicator = (key: keyof RowData) => {
    if (!sortConfig || sortConfig.key !== key) return '↕️';
    return sortConfig.direction === 'asc' ? '↑' : '↓';
  };
  
  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Virtual Scroll Table (10,000 rows)</h2>
      <div
        ref={containerRef}
        style={styles.tableContainer}
        onScroll={handleScroll}
      >
        <table ref={tableRef} style={styles.table}>
          <thead style={styles.header}>
            <tr>
              <th style={styles.th}>
                <button
                  style={styles.sortButton}
                  onClick={() => handleSort('id')}
                >
                  ID {getSortIndicator('id')}
                </button>
              </th>
              <th style={styles.th}>
                <button
                  style={styles.sortButton}
                  onClick={() => handleSort('name')}
                >
                  Name {getSortIndicator('name')}
                </button>
              </th>
              <th style={styles.th}>
                <button
                  style={styles.sortButton}
                  onClick={() => handleSort('email')}
                >
                  Email {getSortIndicator('email')}
                </button>
              </th>
              <th style={styles.th}>
                <button
                  style={styles.sortButton}
                  onClick={() => handleSort('age')}
                >
                  Age {getSortIndicator('age')}
                </button>
              </th>
            </tr>
          </thead>
          <tbody style={{ height: totalHeight - headerHeight }}>
            <tr style={{ height: startIndex * rowHeight }} />
            {visibleData.map((row, index) => (
              <tr
                key={row.id}
                style={{
                  ...styles.tr,
                  height: rowHeight,
                  position: 'absolute',
                  top: (startIndex + index) * rowHeight + headerHeight,
                  width: '100%',
                }}
              >
                <td style={styles.td}>{row.id}</td>
                <td style={styles.td}>{row.name}</td>
                <td style={styles.td}>{row.email}</td>
                <td style={styles.td}>{row.age}</td>
              </tr>
            ))}
            <tr style={{ height: (data.length - endIndex) * rowHeight }} />
          </tbody>
        </table>
      </div>
      <div style={styles.stats}>
        Showing rows {startIndex + 1} to {endIndex} of {data.length} | 
        Sorted by: {sortConfig ? `${sortConfig.key} ${sortConfig.direction}` : 'none'}
      </div>
    </div>
  );
};

/* CSS Module content as comment block */
/*
.tableContainer {
  height: 600px;
  overflow-y: auto;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.header {
  position: sticky;
  top: 0;
  background-color: #f8f9fa;
  z-index: 10;
}

.th {
  padding: 12px;
  text-align: left;
  border-bottom: 2px solid #dee2e6;
  font-weight: 600;
}

.sortButton {
  background: none;
  border: none;
  font-weight: inherit;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
}

.tr {
  border-bottom: 1px solid #e9ecef;
}

.td {
  padding: 12px;
  border-bottom: 1px solid #e9ecef;
}

.tr:nth-child(even) {
  background-color: #f8f9fa;
}

.tr:hover {
  background-color: #e9ecef;
}
*/

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    fontFamily: 'Arial, sans-serif',
    maxWidth: '900px',
    margin: '0 auto',
    padding: '20px',
  },
  title: {
    textAlign: 'center',
    marginBottom: '20px',
    color: '#333',
  },
  tableContainer: {
    height: '600px',
    overflowY: 'auto',
    border: '1px solid #ddd',
    borderRadius: '4px',
    position: 'relative',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    tableLayout: 'fixed',
  },
  header: {
    position: 'sticky',
    top: 0,
    backgroundColor: '#f8f9fa',
    zIndex: 10,
  },
  th: {
    padding: '12px',
    textAlign: 'left',
    borderBottom: '2px solid #dee2e6',
    fontWeight: 600,
    width: '25%',
  },
  sortButton: {
    background: 'none',
    border: 'none',
    fontWeight: 'inherit',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '14px',
    color: '#495057',
  },
  tr: {
    borderBottom: '1px solid #e9ecef',
    backgroundColor: 'white',
    boxSizing: 'border-box',
    left: 0,
    right: 0,
  },
  td: {
    padding: '12px',
    borderBottom: '1px solid #e9ecef',
    width: '25%',
    boxSizing: 'border-box',
  },
  stats: {
    marginTop: '15px',
    fontSize: '14px',
    color: '#6c757d',
    textAlign: 'center',
  },
};

export default VirtualScrollTable;