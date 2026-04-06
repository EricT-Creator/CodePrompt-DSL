import React, { useState, useMemo, useRef, useEffect, useCallback } from 'react';

interface Row {
  id: number;
  name: string;
  email: string;
  age: number;
  city: string;
  job: string;
}

type SortKey = 'name' | 'email' | 'age';
type SortOrder = 'asc' | 'desc';

const ROW_HEIGHT = 40;
const OVERSCAN = 5;
const CONTAINER_HEIGHT = 400;
const TOTAL_ROWS = 10000;

function generateData(count: number): Row[] {
  const cities = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix'];
  const jobs = ['Engineer', 'Designer', 'Manager', 'Developer', 'Analyst'];
  
  return Array.from({ length: count }, (_, i) => ({
    id: i + 1,
    name: `Person ${i + 1}`,
    email: `person${i + 1}@example.com`,
    age: 20 + (i % 50),
    city: cities[i % cities.length],
    job: jobs[i % jobs.length],
  }));
}

const styles = `
/* CSS Module Styles */
.container {
  max-width: 800px;
  margin: 40px auto;
  font-family: system-ui, -apple-system, sans-serif;
}

.tableWrapper {
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
}

.header {
  display: flex;
  background-color: #f5f5f5;
  border-bottom: 2px solid #ddd;
  font-weight: 600;
}

.headerCell {
  flex: 1;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
  display: flex;
  align-items: center;
  gap: 8px;
}

.headerCell:hover {
  background-color: #e8e8e8;
}

.sortIndicator {
  font-size: 12px;
  color: #666;
}

.viewport {
  height: ${CONTAINER_HEIGHT}px;
  overflow-y: auto;
  position: relative;
}

.spacer {
  position: relative;
}

.row {
  display: flex;
  height: ${ROW_HEIGHT}px;
  border-bottom: 1px solid #eee;
  position: absolute;
  left: 0;
  right: 0;
}

.row:hover {
  background-color: #f9f9f9;
}

.cell {
  flex: 1;
  padding: 10px 16px;
  display: flex;
  align-items: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.title {
  margin-bottom: 16px;
  color: #333;
}

.info {
  margin-top: 12px;
  color: #666;
  font-size: 14px;
}
`;

export default function VirtualScrollTable() {
  const [sortKey, setSortKey] = useState<SortKey>('name');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');
  const [scrollTop, setScrollTop] = useState(0);
  const viewportRef = useRef<HTMLDivElement>(null);

  const data = useMemo(() => generateData(TOTAL_ROWS), []);

  const sortedData = useMemo(() => {
    const sorted = [...data];
    sorted.sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });
    return sorted;
  }, [data, sortKey, sortOrder]);

  const handleSort = useCallback((key: SortKey) => {
    if (sortKey === key) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortOrder('asc');
    }
  }, [sortKey, sortOrder]);

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  }, []);

  const virtualItems = useMemo(() => {
    const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
    const visibleCount = Math.ceil(CONTAINER_HEIGHT / ROW_HEIGHT);
    const endIndex = Math.min(sortedData.length, startIndex + visibleCount + OVERSCAN * 2);
    
    return {
      startIndex,
      endIndex,
      items: sortedData.slice(startIndex, endIndex),
      totalHeight: sortedData.length * ROW_HEIGHT,
    };
  }, [scrollTop, sortedData]);

  return (
    <div className="container">
      <style>{styles}</style>
      <h2 className="title">Virtual Scroll Table ({TOTAL_ROWS.toLocaleString()} rows)</h2>
      
      <div className="tableWrapper">
        <div className="header">
          <div className="headerCell" onClick={() => handleSort('name')}>
            Name
            {sortKey === 'name' && (
              <span className="sortIndicator">{sortOrder === 'asc' ? '▲' : '▼'}</span>
            )}
          </div>
          <div className="headerCell" onClick={() => handleSort('email')}>
            Email
            {sortKey === 'email' && (
              <span className="sortIndicator">{sortOrder === 'asc' ? '▲' : '▼'}</span>
            )}
          </div>
          <div className="headerCell" onClick={() => handleSort('age')}>
            Age
            {sortKey === 'age' && (
              <span className="sortIndicator">{sortOrder === 'asc' ? '▲' : '▼'}</span>
            )}
          </div>
        </div>
        
        <div className="viewport" ref={viewportRef} onScroll={handleScroll}>
          <div className="spacer" style={{ height: virtualItems.totalHeight }}>
            {virtualItems.items.map((row, index) => {
              const actualIndex = virtualItems.startIndex + index;
              return (
                <div
                  key={row.id}
                  className="row"
                  style={{ top: actualIndex * ROW_HEIGHT }}
                >
                  <div className="cell">{row.name}</div>
                  <div className="cell">{row.email}</div>
                  <div className="cell">{row.age}</div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
      
      <p className="info">
        Showing rows {virtualItems.startIndex + 1} - {Math.min(virtualItems.endIndex, sortedData.length)} of {sortedData.length} | 
        Sort: {sortKey} ({sortOrder})
      </p>
    </div>
  );
}
