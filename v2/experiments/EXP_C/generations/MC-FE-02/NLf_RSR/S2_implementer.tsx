import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';

// ===================== Interfaces =====================

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

interface GridState {
  data: RowData[];
  filteredData: RowData[];
  sortConfig: SortConfig;
  filterText: string;
  scrollTop: number;
  startIndex: number;
  endIndex: number;
  viewportHeight: number;
}

// ===================== Mock Data Generation =====================

function generateMockData(): RowData[] {
  const departments = ['Engineering', 'Marketing', 'Sales', 'HR', 'Finance', 'Product', 'Design'];
  const names = [
    'Alice Johnson', 'Bob Smith', 'Charlie Brown', 'Diana Prince', 'Edward Miller',
    'Fiona Chen', 'George Wilson', 'Hannah Lee', 'Ian Davis', 'Julia Garcia',
    'Kevin Martin', 'Lisa Taylor', 'Michael Wang', 'Nancy Anderson', 'Oliver Clark',
    'Patricia Lewis', 'Quinn Rodriguez', 'Rachel Hall', 'Samuel White', 'Tina Young'
  ];

  const data: RowData[] = [];
  for (let i = 1; i <= 10000; i++) {
    const name = names[i % names.length] + ` ${i}`;
    const email = `${name.toLowerCase().replace(/\s+/g, '.')}@company.com`;
    const age = 22 + (i % 40);
    const department = departments[i % departments.length];
    const salary = 50000 + (i % 100) * 1000;

    data.push({
      id: i,
      name,
      email,
      age,
      department,
      salary,
    });
  }
  return data;
}

// ===================== Components =====================

const GridToolbar: React.FC<{
  filterText: string;
  onFilterChange: (text: string) => void;
}> = ({ filterText, onFilterChange }) => {
  const [debouncedText, setDebouncedText] = useState(filterText);
  
  useEffect(() => {
    const timer = setTimeout(() => {
      onFilterChange(debouncedText);
    }, 200);
    return () => clearTimeout(timer);
  }, [debouncedText, onFilterChange]);

  return (
    <div className="grid-toolbar">
      <input
        type="text"
        placeholder="Search in name, email, department..."
        value={debouncedText}
        onChange={(e) => setDebouncedText(e.target.value)}
        className="search-input"
      />
      <span className="search-hint">Search across name, email, and department columns</span>
    </div>
  );
};

const SortableColumnHeader: React.FC<{
  columnKey: keyof RowData;
  label: string;
  sortConfig: SortConfig;
  onSort: (key: keyof RowData) => void;
}> = ({ columnKey, label, sortConfig, onSort }) => {
  const isSorted = sortConfig?.key === columnKey;
  const direction = isSorted ? sortConfig.direction : null;

  return (
    <th
      className={`column-header ${isSorted ? 'sorted' : ''}`}
      onClick={() => onSort(columnKey)}
    >
      <div className="header-content">
        <span>{label}</span>
        {isSorted && (
          <span className={`sort-arrow ${direction === 'asc' ? 'asc' : 'desc'}`}>
            {direction === 'asc' ? '↑' : '↓'}
          </span>
        )}
      </div>
    </th>
  );
};

const GridHeader: React.FC<{
  sortConfig: SortConfig;
  onSort: (key: keyof RowData) => void;
}> = ({ sortConfig, onSort }) => {
  return (
    <div className="grid-header">
      <table className="header-table">
        <thead>
          <tr>
            <SortableColumnHeader
              columnKey="id"
              label="ID"
              sortConfig={sortConfig}
              onSort={onSort}
            />
            <SortableColumnHeader
              columnKey="name"
              label="Name"
              sortConfig={sortConfig}
              onSort={onSort}
            />
            <SortableColumnHeader
              columnKey="email"
              label="Email"
              sortConfig={sortConfig}
              onSort={onSort}
            />
            <SortableColumnHeader
              columnKey="age"
              label="Age"
              sortConfig={sortConfig}
              onSort={onSort}
            />
            <SortableColumnHeader
              columnKey="department"
              label="Department"
              sortConfig={sortConfig}
              onSort={onSort}
            />
            <SortableColumnHeader
              columnKey="salary"
              label="Salary"
              sortConfig={sortConfig}
              onSort={onSort}
            />
          </tr>
        </thead>
      </table>
    </div>
  );
};

const GridRow: React.FC<{
  row: RowData;
  style: React.CSSProperties;
}> = ({ row, style }) => {
  return (
    <tr className="grid-row" style={style}>
      <td className="cell">{row.id}</td>
      <td className="cell">{row.name}</td>
      <td className="cell">{row.email}</td>
      <td className="cell">{row.age}</td>
      <td className="cell">{row.department}</td>
      <td className="cell">${row.salary.toLocaleString()}</td>
    </tr>
  );
};

const VirtualRows: React.FC<{
  rows: RowData[];
  startIndex: number;
  rowHeight: number;
}> = ({ rows, startIndex, rowHeight }) => {
  return (
    <div className="virtual-rows">
      {rows.map((row, index) => (
        <GridRow
          key={row.id}
          row={row}
          style={{
            position: 'absolute',
            top: `${(startIndex + index) * rowHeight}px`,
            width: '100%',
          }}
        />
      ))}
    </div>
  );
};

const ScrollContainer: React.FC<{
  totalHeight: number;
  rowHeight: number;
  overscan: number;
  filteredSortedData: RowData[];
  onScroll: (scrollTop: number, viewportHeight: number) => void;
  children: React.ReactNode;
}> = ({ totalHeight, rowHeight, overscan, filteredSortedData, onScroll, children }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [prevScroll, setPrevScroll] = useState({ start: 0, end: 0 });

  const handleScroll = useCallback(() => {
    if (!containerRef.current) return;

    const scrollTop = containerRef.current.scrollTop;
    const viewportHeight = containerRef.current.clientHeight;
    
    const startIndex = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan);
    const endIndex = Math.min(
      filteredSortedData.length,
      Math.ceil((scrollTop + viewportHeight) / rowHeight) + overscan
    );

    // Only update if range actually changed
    if (startIndex !== prevScroll.start || endIndex !== prevScroll.end) {
      setPrevScroll({ start: startIndex, end: endIndex });
      onScroll(scrollTop, viewportHeight);
    }
  }, [rowHeight, overscan, filteredSortedData.length, onScroll, prevScroll]);

  useEffect(() => {
    if (containerRef.current) {
      const viewportHeight = containerRef.current.clientHeight;
      handleScroll(); // Initial calculation
    }
  }, [handleScroll]);

  return (
    <div
      ref={containerRef}
      className="scroll-container"
      onScroll={handleScroll}
      style={{ height: 'calc(100vh - 200px)' }}
    >
      <div
        className="scroll-spacer"
        style={{ height: `${totalHeight}px`, position: 'relative' }}
      >
        {children}
      </div>
    </div>
  );
};

// ===================== Main Component =====================

const VirtualDataGrid: React.FC = () => {
  const ROW_HEIGHT = 36;
  const OVERSCAN = 5;
  
  const [state, setState] = useState<GridState>({
    data: generateMockData(),
    filteredData: [],
    sortConfig: null,
    filterText: '',
    scrollTop: 0,
    startIndex: 0,
    endIndex: 0,
    viewportHeight: 600,
  });

  // Filter data
  const filteredData = useMemo(() => {
    if (!state.filterText.trim()) return state.data;
    
    const searchText = state.filterText.toLowerCase();
    return state.data.filter(row =>
      row.name.toLowerCase().includes(searchText) ||
      row.email.toLowerCase().includes(searchText) ||
      row.department.toLowerCase().includes(searchText)
    );
  }, [state.data, state.filterText]);

  // Sort data
  const filteredSortedData = useMemo(() => {
    const data = [...filteredData];
    if (!state.sortConfig) return data;

    const { key, direction } = state.sortConfig;
    return data.sort((a, b) => {
      const aVal = a[key];
      const bVal = b[key];

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return direction === 'asc'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      } else {
        return direction === 'asc'
          ? (aVal as number) - (bVal as number)
          : (bVal as number) - (aVal as number);
      }
    });
  }, [filteredData, state.sortConfig]);

  // Calculate visible rows
  const visibleRows = useMemo(() => {
    return filteredSortedData.slice(state.startIndex, state.endIndex);
  }, [filteredSortedData, state.startIndex, state.endIndex]);

  const handleFilterChange = useCallback((text: string) => {
    setState(prev => ({ ...prev, filterText: text }));
  }, []);

  const handleSort = useCallback((key: keyof RowData) => {
    setState(prev => {
      if (prev.sortConfig?.key === key) {
        if (prev.sortConfig.direction === 'asc') {
          return { ...prev, sortConfig: { key, direction: 'desc' } };
        } else {
          return { ...prev, sortConfig: null };
        }
      } else {
        return { ...prev, sortConfig: { key, direction: 'asc' } };
      }
    });
  }, []);

  const handleScroll = useCallback((scrollTop: number, viewportHeight: number) => {
    const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
    const endIndex = Math.min(
      filteredSortedData.length,
      Math.ceil((scrollTop + viewportHeight) / ROW_HEIGHT) + OVERSCAN
    );

    setState(prev => ({
      ...prev,
      scrollTop,
      viewportHeight,
      startIndex,
      endIndex,
    }));
  }, [filteredSortedData.length, ROW_HEIGHT, OVERSCAN]);

  return (
    <div className="virtual-data-grid">
      <style>{`
        .virtual-data-grid {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
          height: 100vh;
          display: flex;
          flex-direction: column;
          background-color: #fafafa;
        }

        .grid-toolbar {
          padding: 16px 24px;
          background-color: white;
          border-bottom: 1px solid #e0e0e0;
          box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        .search-input {
          width: 100%;
          padding: 10px 16px;
          border: 1px solid #ddd;
          border-radius: 6px;
          font-size: 14px;
          transition: border-color 0.2s;
        }

        .search-input:focus {
          outline: none;
          border-color: #2196f3;
          box-shadow: 0 0 0 2px rgba(33,150,243,0.1);
        }

        .search-hint {
          display: block;
          margin-top: 8px;
          font-size: 12px;
          color: #666;
        }

        .grid-header {
          position: sticky;
          top: 0;
          z-index: 10;
          background-color: white;
          border-bottom: 2px solid #1976d2;
        }

        .header-table {
          width: 100%;
          border-collapse: collapse;
          table-layout: fixed;
        }

        .column-header {
          padding: 12px 16px;
          text-align: left;
          font-weight: 600;
          color: #333;
          border-right: 1px solid #e0e0e0;
          cursor: pointer;
          user-select: none;
          background-color: #f5f5f5;
          transition: background-color 0.2s;
        }

        .column-header:hover {
          background-color: #eeeeee;
        }

        .column-header.sorted {
          background-color: #e3f2fd;
          color: #1976d2;
        }

        .header-content {
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .sort-arrow {
          font-size: 12px;
          margin-left: 8px;
          opacity: 0.8;
        }

        .sort-arrow.asc {
          transform: rotate(0deg);
        }

        .sort-arrow.desc {
          transform: rotate(180deg);
        }

        .scroll-container {
          overflow-y: auto;
          overflow-x: hidden;
          background-color: white;
          border: 1px solid #e0e0e0;
          margin: 0 24px 24px;
          border-radius: 6px;
        }

        .virtual-rows {
          position: absolute;
          width: 100%;
        }

        .grid-row {
          display: table;
          width: 100%;
          table-layout: fixed;
          border-bottom: 1px solid #f0f0f0;
          transition: background-color 0.1s;
        }

        .grid-row:hover {
          background-color: #f8f9fa;
        }

        .cell {
          padding: 10px 16px;
          font-size: 13px;
          color: #333;
          border-right: 1px solid #f0f0f0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .grid-stats {
          padding: 12px 24px;
          background-color: white;
          border-top: 1px solid #e0e0e0;
          font-size: 13px;
          color: #666;
          display: flex;
          justify-content: space-between;
        }

        .stat-item {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .stat-label {
          font-weight: 500;
          color: #333;
        }

        .stat-value {
          font-family: 'Monaco', 'Menlo', monospace;
          background-color: #f5f5f5;
          padding: 2px 6px;
          border-radius: 4px;
        }
      `}</style>

      <GridToolbar
        filterText={state.filterText}
        onFilterChange={handleFilterChange}
      />

      <GridHeader
        sortConfig={state.sortConfig}
        onSort={handleSort}
      />

      <ScrollContainer
        totalHeight={filteredSortedData.length * ROW_HEIGHT}
        rowHeight={ROW_HEIGHT}
        overscan={OVERSCAN}
        filteredSortedData={filteredSortedData}
        onScroll={handleScroll}
      >
        <VirtualRows
          rows={visibleRows}
          startIndex={state.startIndex}
          rowHeight={ROW_HEIGHT}
        />
      </ScrollContainer>

      <div className="grid-stats">
        <div className="stat-item">
          <span className="stat-label">Total Rows:</span>
          <span className="stat-value">{state.data.length.toLocaleString()}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Filtered Rows:</span>
          <span className="stat-value">{filteredSortedData.length.toLocaleString()}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Visible Rows:</span>
          <span className="stat-value">{visibleRows.length} ({state.startIndex}-{state.endIndex})</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Sort:</span>
          <span className="stat-value">
            {state.sortConfig
              ? `${state.sortConfig.key} ${state.sortConfig.direction}`
              : 'None'}
          </span>
        </div>
      </div>
    </div>
  );
};

export default VirtualDataGrid;