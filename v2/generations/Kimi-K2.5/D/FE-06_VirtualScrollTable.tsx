import React, { useState, useRef, useMemo, useCallback } from 'react';

interface DataRow {
  id: number;
  name: string;
  age: number;
  city: string;
}

const ROW_HEIGHT = 40;
const VISIBLE_ROWS = 15;
const BUFFER_ROWS = 5;

const generateData = (): DataRow[] => {
  const data: DataRow[] = [];
  for (let i = 1; i <= 10000; i++) {
    data.push({
      id: i,
      name: `用户${i}`,
      age: 20 + (i % 50),
      city: ['北京', '上海', '广州', '深圳', '杭州'][i % 5],
    });
  }
  return data;
};

type SortKey = 'name' | 'age' | 'city';
type SortOrder = 'asc' | 'desc';

export default function VirtualScrollTable() {
  const [data] = useState<DataRow[]>(generateData);
  const [sortKey, setSortKey] = useState<SortKey | null>(null);
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const sortedData = useMemo(() => {
    if (!sortKey) return data;
    return [...data].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });
  }, [data, sortKey, sortOrder]);

  const handleSort = useCallback((key: SortKey) => {
    if (sortKey === key) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortOrder('asc');
    }
  }, [sortKey, sortOrder]);

  const totalHeight = sortedData.length * ROW_HEIGHT;
  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - BUFFER_ROWS);
  const endIndex = Math.min(
    sortedData.length,
    Math.ceil((scrollTop + VISIBLE_ROWS * ROW_HEIGHT) / ROW_HEIGHT) + BUFFER_ROWS
  );
  const visibleData = sortedData.slice(startIndex, endIndex);
  const offsetY = startIndex * ROW_HEIGHT;

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  }, []);

  const getSortIcon = (key: SortKey) => {
    if (sortKey !== key) return '↕';
    return sortOrder === 'asc' ? '↑' : '↓';
  };

  return (
    <div className="container">
      <h2>万行虚拟滚动表格</h2>
      <div className="table-wrapper" ref={containerRef} onScroll={handleScroll}>
        <div className="table-container">
          <div className="table-header">
            <div className="header-cell id-col">ID</div>
            <div className="header-cell sortable" onClick={() => handleSort('name')}>
              姓名 {getSortIcon('name')}
            </div>
            <div className="header-cell sortable age-col" onClick={() => handleSort('age')}>
              年龄 {getSortIcon('age')}
            </div>
            <div className="header-cell sortable" onClick={() => handleSort('city')}>
              城市 {getSortIcon('city')}
            </div>
          </div>
          <div className="table-body" style={{ height: totalHeight }}>
            <div className="visible-rows" style={{ transform: `translateY(${offsetY}px)` }}>
              {visibleData.map((row) => (
                <div key={row.id} className="table-row">
                  <div className="cell id-col">{row.id}</div>
                  <div className="cell">{row.name}</div>
                  <div className="cell age-col">{row.age}</div>
                  <div className="cell">{row.city}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      <div className="info">共 {sortedData.length} 条记录 | 显示第 {startIndex + 1} - {endIndex} 行</div>
    </div>
  );
}

/*
=== CSS模块内容 ===

.container {
  padding: 20px;
  font-family: Arial, sans-serif;
}

.table-wrapper {
  height: 600px;
  overflow: auto;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.table-container {
  display: flex;
  flex-direction: column;
}

.table-header {
  display: flex;
  background-color: #f5f5f5;
  border-bottom: 2px solid #ddd;
  position: sticky;
  top: 0;
  z-index: 1;
}

.header-cell {
  padding: 12px 16px;
  font-weight: bold;
  flex: 1;
  border-right: 1px solid #ddd;
}

.header-cell.id-col {
  flex: 0 0 80px;
}

.header-cell.age-col {
  flex: 0 0 100px;
}

.header-cell:last-child {
  border-right: none;
}

.sortable {
  cursor: pointer;
  user-select: none;
}

.sortable:hover {
  background-color: #e0e0e0;
}

.table-body {
  position: relative;
}

.visible-rows {
  position: absolute;
  width: 100%;
}

.table-row {
  display: flex;
  border-bottom: 1px solid #eee;
  height: 40px;
  align-items: center;
}

.table-row:hover {
  background-color: #f9f9f9;
}

.cell {
  padding: 8px 16px;
  flex: 1;
  border-right: 1px solid #eee;
}

.cell.id-col {
  flex: 0 0 80px;
}

.cell.age-col {
  flex: 0 0 100px;
}

.cell:last-child {
  border-right: none;
}

.info {
  margin-top: 10px;
  color: #666;
  font-size: 14px;
}
*/
