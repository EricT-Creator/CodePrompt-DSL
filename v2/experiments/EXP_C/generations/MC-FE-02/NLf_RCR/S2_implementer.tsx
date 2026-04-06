import React, { useState, useMemo, useCallback, useRef, useEffect } from 'react';

interface RowData {
  id: number;
  name: string;
  email: string;
  age: number;
  department: string;
  salary: number;
}

interface SortConfig {
  key: keyof RowData;
  direction: 'asc' | 'desc';
} | null;

const ROW_HEIGHT = 36;
const OVERSCAN = 5;
const VIEWPORT_HEIGHT = 400;

function generateMockData(): RowData[] {
  const departments = ['Engineering', 'Sales', 'Marketing', 'HR', 'Finance'];
  const firstNames = ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank', 'Grace', 'Henry', 'Ivy', 'Jack'];
  const lastNames = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez'];
  
  return Array.from({ length: 10000 }, (_, i) => {
    const firstName = firstNames[i % firstNames.length];
    const lastName = lastNames[Math.floor(i / 10) % lastNames.length];
    return {
      id: i + 1,
      name: `${firstName} ${lastName}`,
      email: `${firstName.toLowerCase()}.${lastName.toLowerCase()}${i}@company.com`,
      age: 25 + (i % 35),
      department: departments[i % departments.length],
      salary: 50000 + (i % 100) * 1000,
    };
  });
}

export default function VirtualDataGrid() {
  const [data] = useState<RowData[]>(() => generateMockData());
  const [filterText, setFilterText] = useState('');
  const [sortConfig, setSortConfig] = useState<SortConfig>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [viewportHeight] = useState(VIEWPORT_HEIGHT);
  const filterTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [debouncedFilter, setDebouncedFilter] = useState('');

  useEffect(() => {
    if (filterTimeoutRef.current) clearTimeout(filterTimeoutRef.current);
    filterTimeoutRef.current = setTimeout(() => setDebouncedFilter(filterText), 200);
    return () => { if (filterTimeoutRef.current) clearTimeout(filterTimeoutRef.current); };
  }, [filterText]);

  const filteredData = useMemo(() => {
    if (!debouncedFilter) return data;
    const lowerFilter = debouncedFilter.toLowerCase();
    return data.filter(row =>
      row.name.toLowerCase().includes(lowerFilter) ||
      row.email.toLowerCase().includes(lowerFilter) ||
      row.department.toLowerCase().includes(lowerFilter)
    );
  }, [data, debouncedFilter]);

  const sortedData = useMemo(() => {
    if (!sortConfig) return filteredData;
    return [...filteredData].sort((a, b) => {
      const aVal = a[sortConfig.key];
      const bVal = b[sortConfig.key];
      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filteredData, sortConfig]);

  const totalHeight = sortedData.length * ROW_HEIGHT;
  
  const { startIndex, endIndex, visibleRows } = useMemo(() => {
    const start = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
    const end = Math.min(sortedData.length, Math.ceil((scrollTop + viewportHeight) / ROW_HEIGHT) + OVERSCAN);
    return { startIndex: start, endIndex: end, visibleRows: sortedData.slice(start, end) };
  }, [scrollTop, viewportHeight, sortedData]);

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => setScrollTop(e.currentTarget.scrollTop), []);

  const handleSort = useCallback((key: keyof RowData) => {
    setSortConfig(current => {
      if (!current || current.key !== key) return { key, direction: 'asc' };
      if (current.direction === 'asc') return { key, direction: 'desc' };
      return null;
    });
  }, []);

  const columns: { key: keyof RowData; label: string }[] = [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Name' },
    { key: 'email', label: 'Email' },
    { key: 'age', label: 'Age' },
    { key: 'department', label: 'Department' },
    { key: 'salary', label: 'Salary' },
  ];

  const getSortIndicator = (key: keyof RowData) => {
    if (!sortConfig || sortConfig.key !== key) return '↕';
    return sortConfig.direction === 'asc' ? '↑' : '↓';
  };

  return (
    <div className="grid-container">
      <style>{`
        .grid-container { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1000px; margin: 20px auto; }
        .grid-toolbar { margin-bottom: 16px; }
        .grid-toolbar input { padding: 8px 12px; font-size: 14px; border: 1px solid #ddd; border-radius: 4px; width: 300px; }
        .grid-header { display: flex; background: #f5f5f5; border-bottom: 2px solid #ddd; font-weight: 600; }
        .header-cell { padding: 10px 12px; cursor: pointer; user-select: none; flex: 1; }
        .header-cell:hover { background: #e8e8e8; }
        .scroll-container { height: ${VIEWPORT_HEIGHT}px; overflow-y: auto; border: 1px solid #ddd; position: relative; }
        .spacer { position: relative; }
        .grid-row { position: absolute; left: 0; right: 0; display: flex; border-bottom: 1px solid #eee; height: ${ROW_HEIGHT}px; align-items: center; }
        .grid-row:hover { background: #f9f9f9; }
        .grid-cell { padding: 8px 12px; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; }
        .grid-info { margin-top: 10px; color: #666; font-size: 12px; }
      `}</style>
      
      <div className="grid-toolbar">
        <input type="text" placeholder="Search..." value={filterText} onChange={e => setFilterText(e.target.value)} />
      </div>
      
      <div className="grid-header">
        {columns.map(col => (
          <div key={col.key} className="header-cell" onClick={() => handleSort(col.key)}>
            {col.label} {getSortIndicator(col.key)}
          </div>
        ))}
      </div>
      
      <div className="scroll-container" onScroll={handleScroll}>
        <div className="spacer" style={{ height: totalHeight }}>
          {visibleRows.map((row, idx) => (
            <div key={row.id} className="grid-row" style={{ top: (startIndex + idx) * ROW_HEIGHT }}>
              <div className="grid-cell">{row.id}</div>
              <div className="grid-cell">{row.name}</div>
              <div className="grid-cell">{row.email}</div>
              <div className="grid-cell">{row.age}</div>
              <div className="grid-cell">{row.department}</div>
              <div className="grid-cell">${row.salary.toLocaleString()}</div>
            </div>
          ))}
        </div>
      </div>
      
      <div className="grid-info">
        Showing {startIndex + 1}-{Math.min(endIndex, sortedData.length)} of {sortedData.length} rows
      </div>
    </div>
  );
}
