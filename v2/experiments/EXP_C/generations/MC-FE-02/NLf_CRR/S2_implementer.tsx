import React, { useRef, useEffect, useCallback, useMemo, useReducer } from 'react';

// ─── Types ───────────────────────────────────────────────────────────────────

interface GridColumn {
  key: string;
  title: string;
  width: number;
  sortable: boolean;
}

interface GridRow {
  id: number;
  [key: string]: unknown;
}

interface SortConfig {
  key: string | null;
  direction: 'asc' | 'desc' | null;
}

interface GridState {
  sortConfig: SortConfig;
  filterText: string;
  scrollTop: number;
  viewportHeight: number;
}

type GridAction =
  | { type: 'SET_SORT'; key: string }
  | { type: 'SET_FILTER'; text: string }
  | { type: 'SET_SCROLL_TOP'; value: number }
  | { type: 'SET_VIEWPORT_HEIGHT'; value: number };

// ─── Constants ───────────────────────────────────────────────────────────────

const ROW_HEIGHT = 40;
const OVERSCAN = 5;
const TOTAL_ROWS = 10000;

const COLUMNS: GridColumn[] = [
  { key: 'id', title: 'ID', width: 80, sortable: true },
  { key: 'name', title: 'Name', width: 180, sortable: true },
  { key: 'email', title: 'Email', width: 240, sortable: true },
  { key: 'role', title: 'Role', width: 120, sortable: true },
  { key: 'status', title: 'Status', width: 100, sortable: true },
  { key: 'createdAt', title: 'Created At', width: 160, sortable: true },
];

// ─── Styles (CSS Module simulation) ──────────────────────────────────────────

const css = {
  container: {
    fontFamily: "'Segoe UI', system-ui, -apple-system, sans-serif",
    border: '1px solid #e0e0e0',
    borderRadius: 8,
    overflow: 'hidden',
    background: '#fff',
    display: 'flex',
    flexDirection: 'column' as const,
    height: '100vh',
    maxWidth: 1000,
    margin: '0 auto',
  },
  filterBar: {
    padding: '12px 16px',
    borderBottom: '1px solid #e0e0e0',
    background: '#fafbfc',
    display: 'flex',
    alignItems: 'center',
    gap: 12,
  },
  searchInput: {
    flex: 1,
    padding: '8px 12px',
    border: '1px solid #ddd',
    borderRadius: 6,
    fontSize: 14,
    outline: 'none',
  },
  headerRow: {
    display: 'flex',
    background: '#f5f7fa',
    borderBottom: '2px solid #e0e0e0',
    fontWeight: 600,
    fontSize: 13,
    color: '#444',
    userSelect: 'none' as const,
  },
  headerCell: {
    padding: '10px 12px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    borderRight: '1px solid #e8eaed',
  },
  scrollContainer: {
    flex: 1,
    overflow: 'auto',
    position: 'relative' as const,
  },
  row: {
    display: 'flex',
    borderBottom: '1px solid #f0f0f0',
    fontSize: 13,
    color: '#333',
  },
  rowEven: {
    background: '#fafbfc',
  },
  rowOdd: {
    background: '#fff',
  },
  cell: {
    padding: '10px 12px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
    borderRight: '1px solid #f0f0f0',
  },
  statusBar: {
    padding: '8px 16px',
    borderTop: '1px solid #e0e0e0',
    background: '#fafbfc',
    fontSize: 12,
    color: '#888',
    display: 'flex',
    justifyContent: 'space-between',
  },
  sortArrow: {
    fontSize: 10,
    marginLeft: 2,
  },
  statusBadge: {
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: 10,
    fontSize: 11,
    fontWeight: 500,
  },
};

// ─── Mock Data ───────────────────────────────────────────────────────────────

const generateMockData = (count: number): GridRow[] => {
  const roles = ['Admin', 'User', 'Editor', 'Viewer', 'Moderator'];
  const statuses = ['Active', 'Inactive'];
  const firstNames = ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank', 'Grace', 'Hank', 'Ivy', 'Jack'];
  const lastNames = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Wilson', 'Moore'];

  return Array.from({ length: count }, (_, i) => ({
    id: i + 1,
    name: `${firstNames[i % firstNames.length]} ${lastNames[(i * 3) % lastNames.length]}`,
    email: `user${i + 1}@example.com`,
    role: roles[i % roles.length],
    status: statuses[i % statuses.length],
    createdAt: new Date(2020 + (i % 5), i % 12, (i % 28) + 1).toLocaleDateString(),
  }));
};

const ALL_DATA = generateMockData(TOTAL_ROWS);

// ─── Reducer ─────────────────────────────────────────────────────────────────

function gridReducer(state: GridState, action: GridAction): GridState {
  switch (action.type) {
    case 'SET_SORT': {
      const { key } = action;
      let direction: 'asc' | 'desc' | null;
      if (state.sortConfig.key === key) {
        if (state.sortConfig.direction === 'asc') direction = 'desc';
        else if (state.sortConfig.direction === 'desc') direction = null;
        else direction = 'asc';
      } else {
        direction = 'asc';
      }
      return {
        ...state,
        sortConfig: { key: direction ? key : null, direction },
        scrollTop: 0,
      };
    }
    case 'SET_FILTER':
      return { ...state, filterText: action.text, scrollTop: 0 };
    case 'SET_SCROLL_TOP':
      return { ...state, scrollTop: action.value };
    case 'SET_VIEWPORT_HEIGHT':
      return { ...state, viewportHeight: action.value };
    default:
      return state;
  }
}

const initialState: GridState = {
  sortConfig: { key: null, direction: null },
  filterText: '',
  scrollTop: 0,
  viewportHeight: 600,
};

// ─── Component ───────────────────────────────────────────────────────────────

const VirtualDataGrid: React.FC = () => {
  const [state, dispatch] = useReducer(gridReducer, initialState);
  const scrollRef = useRef<HTMLDivElement>(null);
  const rafId = useRef<number | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Measure viewport
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        dispatch({ type: 'SET_VIEWPORT_HEIGHT', value: entry.contentRect.height });
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Filter data
  const filteredData = useMemo(() => {
    if (!state.filterText.trim()) return ALL_DATA;
    const lower = state.filterText.toLowerCase();
    return ALL_DATA.filter((row) =>
      Object.values(row).some((val) => String(val).toLowerCase().includes(lower))
    );
  }, [state.filterText]);

  // Sort data
  const sortedData = useMemo(() => {
    const { key, direction } = state.sortConfig;
    if (!key || !direction) return filteredData;
    return [...filteredData].sort((a, b) => {
      const aVal = a[key];
      const bVal = b[key];
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      if (aVal < bVal) return direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return direction === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filteredData, state.sortConfig]);

  // Virtual range
  const totalHeight = sortedData.length * ROW_HEIGHT;
  const visibleCount = Math.ceil(state.viewportHeight / ROW_HEIGHT);
  const rawStart = Math.floor(state.scrollTop / ROW_HEIGHT) - OVERSCAN;
  const startIndex = Math.max(0, rawStart);
  const endIndex = Math.min(sortedData.length, rawStart + visibleCount + OVERSCAN * 2);
  const offsetY = startIndex * ROW_HEIGHT;
  const visibleRows = sortedData.slice(startIndex, endIndex);

  // Scroll handler with rAF throttling
  const handleScroll = useCallback(() => {
    if (rafId.current) return;
    rafId.current = requestAnimationFrame(() => {
      const el = scrollRef.current;
      if (el) {
        dispatch({ type: 'SET_SCROLL_TOP', value: el.scrollTop });
      }
      rafId.current = null;
    });
  }, []);

  // Debounced filter
  const handleFilter = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const text = e.target.value;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      dispatch({ type: 'SET_FILTER', text });
    }, 150);
  }, []);

  const getSortIndicator = (key: string): string => {
    if (state.sortConfig.key !== key) return ' ↕';
    if (state.sortConfig.direction === 'asc') return ' ↑';
    if (state.sortConfig.direction === 'desc') return ' ↓';
    return ' ↕';
  };

  const statusColor = (val: unknown): React.CSSProperties => {
    if (val === 'Active') return { ...css.statusBadge, background: '#e6f4ea', color: '#1e7e34' };
    return { ...css.statusBadge, background: '#fce8e6', color: '#c62828' };
  };

  return (
    <div style={css.container}>
      {/* Filter Bar */}
      <div style={css.filterBar}>
        <span style={{ fontSize: 14, color: '#666' }}>🔍</span>
        <input
          style={css.searchInput}
          placeholder={`Search across ${TOTAL_ROWS.toLocaleString()} rows...`}
          onChange={handleFilter}
          defaultValue={state.filterText}
        />
      </div>

      {/* Header */}
      <div style={css.headerRow}>
        {COLUMNS.map((col) => (
          <div
            key={col.key}
            style={{ ...css.headerCell, width: col.width, minWidth: col.width }}
            onClick={() => col.sortable && dispatch({ type: 'SET_SORT', key: col.key })}
          >
            {col.title}
            {col.sortable && <span style={css.sortArrow}>{getSortIndicator(col.key)}</span>}
          </div>
        ))}
      </div>

      {/* Scroll Container */}
      <div
        ref={scrollRef}
        style={css.scrollContainer}
        onScroll={handleScroll}
      >
        <div style={{ height: totalHeight, position: 'relative' }}>
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, transform: `translateY(${offsetY}px)` }}>
            {visibleRows.map((row, i) => {
              const rowIndex = startIndex + i;
              return (
                <div
                  key={row.id}
                  style={{
                    ...css.row,
                    ...(rowIndex % 2 === 0 ? css.rowEven : css.rowOdd),
                    height: ROW_HEIGHT,
                  }}
                >
                  {COLUMNS.map((col) => (
                    <div key={col.key} style={{ ...css.cell, width: col.width, minWidth: col.width }}>
                      {col.key === 'status' ? (
                        <span style={statusColor(row[col.key])}>{String(row[col.key])}</span>
                      ) : (
                        String(row[col.key] ?? '')
                      )}
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Status Bar */}
      <div style={css.statusBar}>
        <span>
          {sortedData.length === ALL_DATA.length
            ? `${sortedData.length.toLocaleString()} rows`
            : `${sortedData.length.toLocaleString()} / ${ALL_DATA.length.toLocaleString()} rows (filtered)`}
        </span>
        <span>
          Rendering rows {startIndex + 1}–{Math.min(endIndex, sortedData.length)} of {sortedData.length.toLocaleString()}
        </span>
      </div>
    </div>
  );
};

export default VirtualDataGrid;
