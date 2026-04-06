import React, { useState, useRef, useEffect, useCallback } from 'react';

interface RowData {
  id: number;
  name: string;
  age: number;
  department: string;
  salary: number;
  joinDate: string;
  performance: number;
}

const generateData = (count: number): RowData[] => {
  const departments = ['Engineering', 'Marketing', 'Sales', 'HR', 'Finance', 'Operations'];
  const names = ['Alice', 'Bob', 'Charlie', 'David', 'Eva', 'Frank', 'Grace', 'Henry', 'Ivy', 'Jack'];
  
  return Array.from({ length: count }, (_, i) => ({
    id: i + 1,
    name: `${names[i % names.length]} ${String.fromCharCode(65 + (i % 26))}`,
    age: 25 + Math.floor(Math.random() * 40),
    department: departments[i % departments.length],
    salary: 50000 + Math.floor(Math.random() * 100000),
    joinDate: `202${Math.floor(Math.random() * 6)}-${String(Math.floor(Math.random() * 12) + 1).padStart(2, '0')}-${String(Math.floor(Math.random() * 28) + 1).padStart(2, '0')}`,
    performance: Math.floor(Math.random() * 100),
  }));
};

const VirtualScrollTable: React.FC = () => {
  const [data] = useState<RowData[]>(() => generateData(10000));
  const [visibleRange, setVisibleRange] = useState({ start: 0, end: 0 });
  const [sortConfig, setSortConfig] = useState<{ key: keyof RowData; direction: 'asc' | 'desc' } | null>(null);
  const [sortedData, setSortedData] = useState<RowData[]>([]);
  
  const containerRef = useRef<HTMLDivElement>(null);
  const tableRef = useRef<HTMLTableElement>(null);
  
  const ROW_HEIGHT = 48;
  const HEADER_HEIGHT = 56;
  const OVERSCAN = 10;
  const VISIBLE_ROWS = Math.floor(600 / ROW_HEIGHT) || 12;

  useEffect(() => {
    setSortedData([...data]);
  }, [data]);

  useEffect(() => {
    const updateVisibleRange = () => {
      if (!containerRef.current) return;
      
      const scrollTop = containerRef.current.scrollTop;
      const containerHeight = containerRef.current.clientHeight;
      
      const start = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
      const end = Math.min(
        sortedData.length,
        Math.ceil((scrollTop + containerHeight) / ROW_HEIGHT) + OVERSCAN
      );
      
      setVisibleRange({ start, end });
    };

    const container = containerRef.current;
    if (container) {
      updateVisibleRange();
      container.addEventListener('scroll', updateVisibleRange);
      
      return () => container.removeEventListener('scroll', updateVisibleRange);
    }
  }, [sortedData.length, ROW_HEIGHT]);

  useEffect(() => {
    if (!sortConfig) return;
    
    const sorted = [...data].sort((a, b) => {
      const aVal = a[sortConfig.key];
      const bVal = b[sortConfig.key];
      
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortConfig.direction === 'asc' 
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }
      
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortConfig.direction === 'asc' ? aVal - bVal : bVal - aVal;
      }
      
      return 0;
    });
    
    setSortedData(sorted);
  }, [sortConfig, data]);

  const handleSort = (key: keyof RowData) => {
    setSortConfig(current => {
      if (current?.key === key) {
        return current.direction === 'asc' 
          ? { key, direction: 'desc' }
          : null;
      }
      return { key, direction: 'asc' };
    });
  };

  const getSortIndicator = (key: keyof RowData) => {
    if (sortConfig?.key !== key) return '↕';
    return sortConfig.direction === 'asc' ? '↑' : '↓';
  };

  const visibleData = sortedData.slice(visibleRange.start, visibleRange.end);
  const totalHeight = sortedData.length * ROW_HEIGHT;
  const offsetY = visibleRange.start * ROW_HEIGHT;

  const formatCurrency = (amount: number) => {
    return `$${amount.toLocaleString()}`;
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  };

  const getPerformanceColor = (score: number) => {
    if (score >= 80) return '#4caf50';
    if (score >= 60) return '#ff9800';
    return '#f44336';
  };

  return (
    <div className="virtual-scroll-container" ref={containerRef}>
      <h2>虚拟滚动表格 (10,000 行)</h2>
      <p className="table-info">
        显示 {visibleRange.start + 1}-{Math.min(visibleRange.end, sortedData.length)} / {sortedData.length} 行
      </p>
      
      <div className="table-wrapper">
        <table className="virtual-table" ref={tableRef}>
          <thead className="table-header">
            <tr>
              <th className="sticky-header">ID</th>
              <th 
                className="sticky-header sortable"
                onClick={() => handleSort('name')}
              >
                姓名 {getSortIndicator('name')}
              </th>
              <th 
                className="sticky-header sortable"
                onClick={() => handleSort('age')}
              >
                年龄 {getSortIndicator('age')}
              </th>
              <th 
                className="sticky-header sortable"
                onClick={() => handleSort('department')}
              >
                部门 {getSortIndicator('department')}
              </th>
              <th 
                className="sticky-header sortable"
                onClick={() => handleSort('salary')}
              >
                薪资 {getSortIndicator('salary')}
              </th>
              <th>入职日期</th>
              <th>绩效</th>
            </tr>
          </thead>
          
          <tbody className="table-body">
            <tr style={{ height: offsetY }} />
            
            {visibleData.map((row, index) => {
              const actualIndex = visibleRange.start + index;
              return (
                <tr 
                  key={row.id}
                  className={`table-row ${actualIndex % 2 === 0 ? 'even' : 'odd'}`}
                  style={{ height: ROW_HEIGHT }}
                >
                  <td className="cell id-cell">{row.id}</td>
                  <td className="cell name-cell">{row.name}</td>
                  <td className="cell age-cell">{row.age}</td>
                  <td className="cell dept-cell">{row.department}</td>
                  <td className="cell salary-cell">{formatCurrency(row.salary)}</td>
                  <td className="cell date-cell">{formatDate(row.joinDate)}</td>
                  <td className="cell perf-cell">
                    <div className="perf-bar">
                      <div 
                        className="perf-fill"
                        style={{
                          width: `${row.performance}%`,
                          backgroundColor: getPerformanceColor(row.performance),
                        }}
                      />
                      <span className="perf-text">{row.performance}%</span>
                    </div>
                  </td>
                </tr>
              );
            })}
            
            <tr style={{ height: totalHeight - offsetY - (visibleData.length * ROW_HEIGHT) }} />
          </tbody>
        </table>
      </div>

      <div className="table-footer">
        <div className="stats">
          <span>总行数: {sortedData.length.toLocaleString()}</span>
          <span>可见行: {visibleData.length}</span>
          <span>排序: {sortConfig ? `${String(sortConfig.key)} ${sortConfig.direction}` : '无'}</span>
        </div>
        <div className="hint">
          点击表头列进行排序，滚动查看所有数据
        </div>
      </div>

      {/* CSS Modules as comment block */}
      <style>{`
        .virtual-scroll-container {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          height: 600px;
          max-width: 1000px;
          margin: 0 auto;
          display: flex;
          flex-direction: column;
          overflow: hidden;
          border: 1px solid #e0e0e0;
          border-radius: 8px;
          background: #fff;
        }
        
        h2 {
          color: #333;
          margin: 20px 20px 10px;
          font-size: 24px;
        }
        
        .table-info {
          color: #666;
          margin: 0 20px 15px;
          font-size: 14px;
        }
        
        .table-wrapper {
          flex: 1;
          overflow: auto;
          margin: 0 20px;
        }
        
        .virtual-table {
          width: 100%;
          border-collapse: collapse;
          position: relative;
        }
        
        .table-header {
          position: sticky;
          top: 0;
          z-index: 10;
          background: white;
        }
        
        .sticky-header {
          padding: 16px 12px;
          text-align: left;
          font-weight: 600;
          color: #333;
          background: #f8f9fa;
          border-bottom: 2px solid #e0e0e0;
          white-space: nowrap;
          position: sticky;
          top: 0;
        }
        
        .sortable {
          cursor: pointer;
          user-select: none;
          transition: background-color 0.2s;
        }
        
        .sortable:hover {
          background-color: #e3f2fd;
        }
        
        .table-body {
          position: relative;
        }
        
        .table-row {
          transition: background-color 0.2s;
        }
        
        .table-row:hover {
          background-color: #f5f5f5;
        }
        
        .table-row.even {
          background-color: #fafafa;
        }
        
        .table-row.odd {
          background-color: white;
        }
        
        .cell {
          padding: 12px;
          border-bottom: 1px solid #f0f0f0;
          color: #333;
          font-size: 14px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        
        .id-cell {
          width: 60px;
          color: #666;
          font-weight: 500;
        }
        
        .name-cell {
          width: 150px;
          font-weight: 500;
        }
        
        .age-cell {
          width: 80px;
          text-align: right;
        }
        
        .dept-cell {
          width: 120px;
        }
        
        .salary-cell {
          width: 120px;
          text-align: right;
          font-weight: 500;
          color: #1976d2;
        }
        
        .date-cell {
          width: 120px;
          color: #666;
        }
        
        .perf-cell {
          width: 150px;
        }
        
        .perf-bar {
          height: 20px;
          background: #f5f5f5;
          border-radius: 10px;
          overflow: hidden;
          position: relative;
        }
        
        .perf-fill {
          height: 100%;
          border-radius: 10px;
          transition: width 0.3s ease;
        }
        
        .perf-text {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          font-weight: 500;
          color: white;
          text-shadow: 0 1px 1px rgba(0,0,0,0.3);
        }
        
        .table-footer {
          padding: 15px 20px;
          border-top: 1px solid #e0e0e0;
          background: #f8f9fa;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        
        .stats {
          display: flex;
          gap: 20px;
          font-size: 13px;
          color: #666;
        }
        
        .hint {
          font-size: 13px;
          color: #888;
          font-style: italic;
        }
      `}</style>
    </div>
  );
};

export default VirtualScrollTable;