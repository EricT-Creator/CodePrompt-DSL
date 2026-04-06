import React, { useState, useMemo, useRef, useEffect } from 'react';

const ROW_HEIGHT = 40;
const VISIBLE_COUNT = 10;

const VirtualScrollTable: React.FC = () => {
  const [data] = useState(() => Array.from({ length: 10000 }, (_, i) => ({ id: i, name: `Row ${i}`, value: Math.floor(Math.random() * 100) })));
  const [sortConfig, setSortConfig] = useState<{ key: string, direction: 'asc' | 'desc' } | null>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const sortedData = useMemo(() => {
    let sortableData = [...data];
    if (sortConfig !== null) {
      sortableData.sort((a, b) => {
        if (a[sortConfig.key as keyof typeof a] < b[sortConfig.key as keyof typeof b]) return sortConfig.direction === 'asc' ? -1 : 1;
        if (a[sortConfig.key as keyof typeof a] > b[sortConfig.key as keyof typeof a]) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }
    return sortableData;
  }, [data, sortConfig]);

  const startIndex = Math.floor(scrollTop / ROW_HEIGHT);
  const endIndex = Math.min(startIndex + VISIBLE_COUNT + 1, sortedData.length);
  const visibleData = sortedData.slice(startIndex, endIndex);

  return (
    <div ref={containerRef} onScroll={(e) => setScrollTop(e.currentTarget.scrollTop)} style={{ height: ROW_HEIGHT * VISIBLE_COUNT, overflowY: 'auto', position: 'relative' }}>
      <div style={{ height: sortedData.length * ROW_HEIGHT, position: 'relative' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', position: 'absolute', top: startIndex * ROW_HEIGHT }}>
          <thead>
            <tr>
              <th onClick={() => setSortConfig({ key: 'id', direction: sortConfig?.direction === 'asc' ? 'desc' : 'asc' })}>ID</th>
              <th onClick={() => setSortConfig({ key: 'name', direction: sortConfig?.direction === 'asc' ? 'desc' : 'asc' })}>Name</th>
              <th onClick={() => setSortConfig({ key: 'value', direction: sortConfig?.direction === 'asc' ? 'desc' : 'asc' })}>Value</th>
            </tr>
          </thead>
          <tbody>
            {visibleData.map(row => (
              <tr key={row.id} style={{ height: ROW_HEIGHT }}>
                <td>{row.id}</td>
                <td>{row.name}</td>
                <td>{row.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default VirtualScrollTable;

/*
.table { width: 100%; border-collapse: collapse; }
.header { font-weight: bold; cursor: pointer; }
.row { height: 40px; }
*/
