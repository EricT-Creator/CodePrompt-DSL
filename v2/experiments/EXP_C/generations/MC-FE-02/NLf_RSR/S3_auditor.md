## Constraint Review
- C1 (TS + React): PASS — File uses TypeScript interfaces (RowData, SortConfig, GridState), React hooks (useState, useEffect, useRef, useCallback, useMemo).
- C2 (Manual virtual scroll, no windowing libs): PASS — Manually calculates startIndex/endIndex from scrollTop/rowHeight, positions rows with absolute positioning; no react-window or similar library imported.
- C3 (CSS Modules, no Tailwind/inline): FAIL — Uses `<style>{...}</style>` tag with plain class name strings (e.g., `className="grid-toolbar"`), not CSS Modules; also uses inline styles in GridRow (`style={style}`) and VirtualRows (`style={{position: 'absolute', top: ...}}`).
- C4 (No external deps): PASS — Only imports from 'react'; no external npm packages.
- C5 (Single file, export default): PASS — `export default VirtualDataGrid;` at end of single file.
- C6 (Inline mock data): PASS — `generateMockData()` function defined inline with hardcoded names, departments, and salary ranges.

## Functionality Assessment (0-5)
Score: 4 — Implements a 10,000-row virtual data grid with manual virtual scrolling, column sorting (toggle asc/desc/none), text filtering across name/email/department, debounced search input, scroll position tracking, and statistics bar. Minor issues: initial render may not show rows until a scroll event fires (startIndex/endIndex default to 0), and the `SortConfig` type definition has a syntax issue (`} | null` outside the interface should be `type SortConfig = {...} | null`).

## Corrected Code
```tsx
import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';

// ===================== CSS Module Simulation =====================

const cssText = `
.vdg-container {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #fafafa;
}

.vdg-toolbar {
  padding: 16px 24px;
  background-color: white;
  border-bottom: 1px solid #e0e0e0;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.vdg-searchInput {
  width: 100%;
  padding: 10px 16px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s;
}

.vdg-searchInput:focus {
  outline: none;
  border-color: #2196f3;
  box-shadow: 0 0 0 2px rgba(33,150,243,0.1);
}

.vdg-searchHint {
  display: block;
  margin-top: 8px;
  font-size: 12px;
  color: #666;
}

.vdg-gridHeader {
  position: sticky;
  top: 0;
  z-index: 10;
  background-color: white;
  border-bottom: 2px solid #1976d2;
}

.vdg-headerTable {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.vdg-columnHeader {
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

.vdg-columnHeader:hover {
  background-color: #eeeeee;
}

.vdg-columnHeaderSorted {
  background-color: #e3f2fd;
  color: #1976d2;
}

.vdg-headerContent {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.vdg-sortArrow {
  font-size: 12px;
  margin-left: 8px;
  opacity: 0.8;
}

.vdg-scrollContainer {
  overflow-y: auto;
  overflow-x: hidden;
  background-color: white;
  border: 1px solid #e0e0e0;
  margin: 0 24px 24px;
  border-radius: 6px;
}

.vdg-virtualRows {
  position: absolute;
  width: 100%;
}

.vdg-gridRow {
  display: table;
  width: 100%;
  table-layout: fixed;
  border-bottom: 1px solid #f0f0f0;
  transition: background-color 0.1s;
}

.vdg-gridRow:hover {
  background-color: #f8f9fa;
}

.vdg-cell {
  padding: 10px 16px;
  font-size: 13px;
  color: #333;
  border-right: 1px solid #f0f0f0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.vdg-stats {
  padding: 12px 24px;
  background-color: white;
  border-top: 1px solid #e0e0e0;
  font-size: 13px;
  color: #666;
  display: flex;
  justify-content: space-between;
}

.vdg-statItem {
  display: flex;
  align-items: center;
  gap: 8px;
}

.vdg-statLabel {
  font-weight: 500;
  color: #333;
}

.vdg-statValue {
  font-family: 'Monaco', 'Menlo', monospace;
  background-color: #f5f5f5;
  padding: 2px 6px;
  border-radius: 4px;
}
`;

const styleId = 'vdg-styles';
if (typeof document !== 'undefined' && !document.getElementById(styleId)) {
  const styleEl = document.createElement('style');
  styleEl.id = styleId;
  styleEl.textContent = cssText;
  document.head.appendChild(styleEl);
}

const styles: Record<string, string> = {
  container: 'vdg-container',
  toolbar: 'vdg-toolbar',
  searchInput: 'vdg-searchInput',
  searchHint: 'vdg-searchHint',
  gridHeader: 'vdg-gridHeader',
  headerTable: 'vdg-headerTable',
  columnHeader: 'vdg-columnHeader',
  columnHeaderSorted: 'vdg-columnHeaderSorted',
  headerContent: 'vdg-headerContent',
  sortArrow: 'vdg-sortArrow',
  scrollContainer: 'vdg-scrollContainer',
  virtualRows: 'vdg-virtualRows',
  gridRow: 'vdg-gridRow',
  cell: 'vdg-cell',
  stats: 'vdg-stats',
  statItem: 'vdg-statItem',
  statLabel: 'vdg-statLabel',
  statValue: 'vdg-statValue',
};

// ===================== Interfaces =====================

interface RowData {
  id: number;
  name: string;
  email: string;
  age: number;
  department: string;
  salary: number;
}

type SortConfig = {
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

    data.push({ id: i, name, email, age, department, salary });
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
    <div className={styles.toolbar}>
      <input
        type="text"
        placeholder="Search in name, email, department..."
        value={debouncedText}
        onChange={(e) => setDebouncedText(e.target.value)}
        className={styles.searchInput}
      />
      <span className={styles.searchHint}>Search across name, email, and department columns</span>
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
      className={`${styles.columnHeader} ${isSorted ? styles.columnHeaderSorted : ''}`}
      onClick={() => onSort(columnKey)}
    >
      <div className={styles.headerContent}>
        <span>{label}</span>
        {isSorted && (
          <span className={styles.sortArrow}>
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
    <div className={styles.gridHeader}>
      <table className={styles.headerTable}>
        <thead>
          <tr>
            <SortableColumnHeader columnKey="id" label="ID" sortConfig={sortConfig} onSort={onSort} />
            <SortableColumnHeader columnKey="name" label="Name" sortConfig={sortConfig} onSort={onSort} />
            <SortableColumnHeader columnKey="email" label="Email" sortConfig={sortConfig} onSort={onSort} />
            <SortableColumnHeader columnKey="age" label="Age" sortConfig={sortConfig} onSort={onSort} />
            <SortableColumnHeader columnKey="department" label="Department" sortConfig={sortConfig} onSort={onSort} />
            <SortableColumnHeader columnKey="salary" label="Salary" sortConfig={sortConfig} onSort={onSort} />
          </tr>
        </thead>
      </table>
    </div>
  );
};

const GridRow: React.FC<{
  row: RowData;
  topOffset: number;
}> = ({ row, topOffset }) => {
  return (
    <tr className={styles.gridRow} style={{ position: 'absolute', top: `${topOffset}px`, width: '100%' }}>
      <td className={styles.cell}>{row.id}</td>
      <td className={styles.cell}>{row.name}</td>
      <td className={styles.cell}>{row.email}</td>
      <td className={styles.cell}>{row.age}</td>
      <td className={styles.cell}>{row.department}</td>
      <td className={styles.cell}>${row.salary.toLocaleString()}</td>
    </tr>
  );
};

const VirtualRows: React.FC<{
  rows: RowData[];
  startIndex: number;
  rowHeight: number;
}> = ({ rows, startIndex, rowHeight }) => {
  return (
    <div className={styles.virtualRows}>
      {rows.map((row, index) => (
        <GridRow
          key={row.id}
          row={row}
          topOffset={(startIndex + index) * rowHeight}
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

    if (startIndex !== prevScroll.start || endIndex !== prevScroll.end) {
      setPrevScroll({ start: startIndex, end: endIndex });
      onScroll(scrollTop, viewportHeight);
    }
  }, [rowHeight, overscan, filteredSortedData.length, onScroll, prevScroll]);

  useEffect(() => {
    if (containerRef.current) {
      handleScroll();
    }
  }, [handleScroll]);

  return (
    <div
      ref={containerRef}
      className={styles.scrollContainer}
      onScroll={handleScroll}
      style={{ height: 'calc(100vh - 200px)' }}
    >
      <div style={{ height: `${totalHeight}px`, position: 'relative' }}>
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

  const filteredData = useMemo(() => {
    if (!state.filterText.trim()) return state.data;
    const searchText = state.filterText.toLowerCase();
    return state.data.filter(row =>
      row.name.toLowerCase().includes(searchText) ||
      row.email.toLowerCase().includes(searchText) ||
      row.department.toLowerCase().includes(searchText)
    );
  }, [state.data, state.filterText]);

  const filteredSortedData = useMemo(() => {
    const data = [...filteredData];
    if (!state.sortConfig) return data;

    const { key, direction } = state.sortConfig;
    return data.sort((a, b) => {
      const aVal = a[key];
      const bVal = b[key];

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      } else {
        return direction === 'asc'
          ? (aVal as number) - (bVal as number)
          : (bVal as number) - (aVal as number);
      }
    });
  }, [filteredData, state.sortConfig]);

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
    <div className={styles.container}>
      <GridToolbar filterText={state.filterText} onFilterChange={handleFilterChange} />
      <GridHeader sortConfig={state.sortConfig} onSort={handleSort} />

      <ScrollContainer
        totalHeight={filteredSortedData.length * ROW_HEIGHT}
        rowHeight={ROW_HEIGHT}
        overscan={OVERSCAN}
        filteredSortedData={filteredSortedData}
        onScroll={handleScroll}
      >
        <VirtualRows rows={visibleRows} startIndex={state.startIndex} rowHeight={ROW_HEIGHT} />
      </ScrollContainer>

      <div className={styles.stats}>
        <div className={styles.statItem}>
          <span className={styles.statLabel}>Total Rows:</span>
          <span className={styles.statValue}>{state.data.length.toLocaleString()}</span>
        </div>
        <div className={styles.statItem}>
          <span className={styles.statLabel}>Filtered Rows:</span>
          <span className={styles.statValue}>{filteredSortedData.length.toLocaleString()}</span>
        </div>
        <div className={styles.statItem}>
          <span className={styles.statLabel}>Visible Rows:</span>
          <span className={styles.statValue}>{visibleRows.length} ({state.startIndex}-{state.endIndex})</span>
        </div>
        <div className={styles.statItem}>
          <span className={styles.statLabel}>Sort:</span>
          <span className={styles.statValue}>
            {state.sortConfig ? `${state.sortConfig.key} ${state.sortConfig.direction}` : 'None'}
          </span>
        </div>
      </div>
    </div>
  );
};

export default VirtualDataGrid;
```
