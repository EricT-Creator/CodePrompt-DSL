import React, { useState, useMemo, useRef, useEffect } from 'react';

interface TableData {
  id: number;
  name: string;
  age: number;
  score: number;
}

const VirtualScrollTable: React.FC = () => {
  const [data, setData] = useState<TableData[]>(() => {
    const items: TableData[] = [];
    for (let i = 1; i <= 10000; i++) {
      items.push({
        id: i,
        name: `用户 ${i}`,
        age: Math.floor(Math.random() * 50) + 18,
        score: Math.floor(Math.random() * 1000)
      });
    }
    return items;
  });
  
  const [sortConfig, setSortConfig] = useState<{
    column: keyof TableData | null;
    direction: 'asc' | 'desc';
  }>({ column: null, direction: 'asc' });
  
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const tableRef = useRef<HTMLTableElement>(null);
  
  const rowHeight = 40;
  const headerHeight = 50;
  const visibleRows = 20;
  const bufferRows = 5;
  
  const sortedData = useMemo(() => {
    if (!sortConfig.column) return data;
    
    return [...data].sort((a, b) => {
      const aValue = a[sortConfig.column!];
      const bValue = b[sortConfig.column!];
      
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
  
  const handleSort = (column: keyof TableData) => {
    setSortConfig(prev => ({
      column,
      direction: prev.column === column && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  };
  
  const handleScroll = () => {
    if (containerRef.current) {
      setScrollTop(containerRef.current.scrollTop);
    }
  };
  
  useEffect(() => {
    const container = containerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll);
      return () => container.removeEventListener('scroll', handleScroll);
    }
  }, []);
  
  const startIndex = Math.max(0, Math.floor(scrollTop / rowHeight) - bufferRows);
  const endIndex = Math.min(
    sortedData.length,
    startIndex + visibleRows + bufferRows * 2
  );
  
  const visibleData = sortedData.slice(startIndex, endIndex);
  
  const getSortIndicator = (column: keyof TableData) => {
    if (sortConfig.column !== column) return null;
    return sortConfig.direction === 'asc' ? '↑' : '↓';
  };
  
  const totalHeight = sortedData.length * rowHeight + headerHeight;
  const offsetY = startIndex * rowHeight;
  
  return (
    <div className="virtual-scroll-container">
      <h2 className="table-title">虚拟滚动表格 (共 {sortedData.length.toLocaleString()} 行)</h2>
      <p className="table-subtitle">仅渲染可见区域及缓冲区，支持点击表头排序</p>
      
      <div 
        ref={containerRef}
        className="scroll-container"
        style={{ height: `${visibleRows * rowHeight + headerHeight}px` }}
      >
        <div style={{ height: `${totalHeight}px`, position: 'relative' }}>
          <table ref={tableRef} className="data-table">
            <thead className="table-header">
              <tr>
                <th 
                  className="header-cell sortable"
                  onClick={() => handleSort('id')}
                >
                  <div className="header-content">
                    <span>ID</span>
                    <span className="sort-indicator">{getSortIndicator('id')}</span>
                  </div>
                </th>
                <th 
                  className="header-cell sortable"
                  onClick={() => handleSort('name')}
                >
                  <div className="header-content">
                    <span>姓名</span>
                    <span className="sort-indicator">{getSortIndicator('name')}</span>
                  </div>
                </th>
                <th 
                  className="header-cell sortable"
                  onClick={() => handleSort('age')}
                >
                  <div className="header-content">
                    <span>年龄</span>
                    <span className="sort-indicator">{getSortIndicator('age')}</span>
                  </div>
                </th>
                <th 
                  className="header-cell sortable"
                  onClick={() => handleSort('score')}
                >
                  <div className="header-content">
                    <span>分数</span>
                    <span className="sort-indicator">{getSortIndicator('score')}</span>
                  </div>
                </th>
              </tr>
            </thead>
            
            <tbody>
              {visibleData.map((item, index) => (
                <tr 
                  key={item.id}
                  className={`table-row ${index % 2 === 0 ? 'even-row' : 'odd-row'}`}
                  style={{
                    position: 'absolute',
                    top: `${offsetY + index * rowHeight}px`,
                    width: '100%',
                    height: `${rowHeight}px`
                  }}
                >
                  <td className="table-cell id-cell">{item.id}</td>
                  <td className="table-cell name-cell">{item.name}</td>
                  <td className="table-cell age-cell">{item.age}</td>
                  <td className="table-cell score-cell">
                    <div className="score-container">
                      <span>{item.score}</span>
                      <div 
                        className="score-bar"
                        style={{ width: `${(item.score / 1000) * 100}%` }}
                      ></div>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      
      <div className="table-footer">
        <div className="footer-info">
          <div className="info-item">
            <span className="info-label">当前排序:</span>
            <span className="info-value">
              {sortConfig.column 
                ? `${sortConfig.column} ${sortConfig.direction === 'asc' ? '升序' : '降序'}` 
                : '无'}
            </span>
          </div>
          <div className="info-item">
            <span className="info-label">显示行数:</span>
            <span className="info-value">
              {visibleData.length} / {sortedData.length.toLocaleString()}
            </span>
          </div>
          <div className="info-item">
            <span className="info-label">滚动位置:</span>
            <span className="info-value">
              {Math.floor(scrollTop / rowHeight)} - {Math.floor(scrollTop / rowHeight) + visibleData.length}
            </span>
          </div>
        </div>
        
        <div className="performance-info">
          <div className="perf-item">
            <span className="perf-label">虚拟化:</span>
            <span className="perf-value">开启</span>
          </div>
          <div className="perf-item">
            <span className="perf-label">渲染行:</span>
            <span className="perf-value">{visibleData.length}</span>
          </div>
          <div className="perf-item">
            <span className="perf-label">缓冲区:</span>
            <span className="perf-value">±{bufferRows}行</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VirtualScrollTable;

/*
CSS模块内容：

.virtual-scroll-container {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
  background-color: #f8f9fa;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.table-title {
  text-align: center;
  color: #2c3e50;
  margin-bottom: 8px;
  font-size: 24px;
  font-weight: 600;
}

.table-subtitle {
  text-align: center;
  color: #7f8c8d;
  margin-bottom: 20px;
  font-size: 14px;
}

.scroll-container {
  overflow-y: auto;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  background-color: white;
  position: relative;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.table-header {
  position: sticky;
  top: 0;
  z-index: 10;
  background-color: #3498db;
}

.header-cell {
  padding: 0;
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  font-weight: 600;
  color: white;
  text-align: left;
  height: 50px;
}

.header-cell:last-child {
  border-right: none;
}

.sortable {
  cursor: pointer;
  transition: background-color 0.2s ease;
  user-select: none;
}

.sortable:hover {
  background-color: #2980b9;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  height: 100%;
}

.sort-indicator {
  font-size: 18px;
  margin-left: 8px;
  opacity: 0.9;
}

.table-row {
  border-bottom: 1px solid #e9ecef;
  background-color: white;
}

.table-row:hover {
  background-color: #f8f9fa;
}

.even-row {
  background-color: #f8f9fa;
}

.odd-row {
  background-color: white;
}

.table-cell {
  padding: 0 16px;
  border-right: 1px solid #e9ecef;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  height: 40px;
  vertical-align: middle;
}

.table-cell:last-child {
  border-right: none;
}

.id-cell {
  width: 100px;
  color: #6c757d;
  font-weight: 500;
}

.name-cell {
  width: 250px;
  color: #495057;
  font-weight: 500;
}

.age-cell {
  width: 150px;
  color: #495057;
  text-align: center;
  font-weight: 500;
}

.score-cell {
  width: 300px;
  color: #495057;
}

.score-container {
  position: relative;
  display: flex;
  align-items: center;
  height: 100%;
}

.score-bar {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  background-color: rgba(52, 152, 219, 0.15);
  z-index: 1;
  transition: width 0.3s ease;
}

.score-container span {
  position: relative;
  z-index: 2;
  padding-left: 8px;
}

.table-footer {
  margin-top: 20px;
  padding: 15px;
  background-color: white;
  border-radius: 6px;
  border: 1px solid #dee2e6;
}

.footer-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 15px;
  flex-wrap: wrap;
  gap: 10px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-label {
  color: #6c757d;
  font-size: 14px;
  font-weight: 500;
}

.info-value {
  color: #495057;
  font-weight: 600;
  background-color: #f8f9fa;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 14px;
}

.performance-info {
  display: flex;
  justify-content: center;
  gap: 30px;
  padding-top: 15px;
  border-top: 1px solid #e9ecef;
}

.perf-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.perf-label {
  color: #6c757d;
  font-size: 14px;
}

.perf-value {
  color: #28a745;
  font-weight: 600;
  font-size: 14px;
}
*/