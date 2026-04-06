import React, { useState, useRef, useEffect, useMemo } from 'react';

// CSS Module content as comment block:
/*
.tableContainer {
  height: 400px;
  overflow: auto;
  position: relative;
  border: 1px solid #ccc;
}
.tableWrapper {
  height: 100000px; /* 10000 rows * 10px height */
  position: relative;
}
.row {
  position: absolute;
  width: 100%;
  height: 10px;
  border-bottom: 1px solid #eee;
  display: flex;
}
.cell {
  flex: 1;
}
*/

const ROW_HEIGHT = 10;
const TOTAL_ROWS = 10000;
const VISIBLE_COUNT = 40;

const VirtualScrollTable: React.FC = () => {
  const [scrollTop, setScrollTop] = useState(0);
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const data = useMemo(() => {
    const arr = Array.from({ length: TOTAL_ROWS }, (_, i) => ({
      id: i,
      col1: i,
      col2: Math.random(),
      col3: i % 10,
    }));
    if (sortConfig) {
      arr.sort((a, b) => {
        const valA = a[sortConfig.key as keyof typeof a];
        const valB = b[sortConfig.key as keyof typeof b];
        if (valA < valB) return sortConfig.direction === 'asc' ? -1 : 1;
        if (valA > valB) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }
    return arr;
  }, [sortConfig]);

  const onScroll = () => {
    if (containerRef.current) {
      setScrollTop(containerRef.current.scrollTop);
    }
  };

  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - 5);
  const endIndex = Math.min(TOTAL_ROWS, startIndex + VISIBLE_COUNT + 10);

  const handleSort = (key: string) => {
    setSortConfig((prev) => ({
      key,
      direction: prev?.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif' }}>
      <h3>Virtual Scroll Table</h3>
      <div 
        ref={containerRef}
        onScroll={onScroll}
        style={{ height: '400px', overflow: 'auto', position: 'relative', border: '1px solid #ccc' }}
      >
        <div style={{ display: 'flex', position: 'sticky', top: 0, backgroundColor: '#eee', zIndex: 1 }}>
          {['id', 'col1', 'col2', 'col3'].map((key) => (
            <div key={key} onClick={() => handleSort(key)} style={{ flex: 1, padding: '5px', cursor: 'pointer' }}>
              {key}
            </div>
          ))}
        </div>
        <div style={{ height: `${TOTAL_ROWS * ROW_HEIGHT}px`, position: 'relative' }}>
          {data.slice(startIndex, endIndex).map((row, i) => (
            <div key={row.id} style={{ position: 'absolute', top: `${(startIndex + i) * ROW_HEIGHT}px`, width: '100%', height: `${ROW_HEIGHT}px`, display: 'flex', borderBottom: '1px solid #eee' }}>
              <div style={{ flex: 1 }}>{row.id}</div>
              <div style={{ flex: 1 }}>{row.col1}</div>
              <div style={{ flex: 1 }}>{row.col2.toFixed(2)}</div>
              <div style={{ flex: 1 }}>{row.col3}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default VirtualScrollTable;
