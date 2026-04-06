import React, { useState, useRef, useMemo, useCallback, useEffect } from 'react';

// ─── Types ───────────────────────────────────────────────────────────────────

interface DataRow {
  id: string | number;
  [key: string]: unknown;
}

interface ColumnDef {
  key: string;
  header: string;
  width: number;
  sortable: boolean;
}

interface VirtualMetrics {
  startIndex: number;
  endIndex: number;
  visibleCount: number;
  totalHeight: number;
  offsetY: number;
}

// ─── Constants ───────────────────────────────────────────────────────────────

const ROW_HEIGHT = 40;
const OVERSCAN = 5;
const CONTAINER_HEIGHT = 400;
const TOTAL_ROWS = 10000;

// ─── Inline styles (CSS modules approach, no Tailwind) ───────────────────────

const css: Record<string, React.CSSProperties> = {
  wrapper: {
    fontFamily: 'system-ui, -apple-system, sans-serif',
    maxWidth: 900,
    margin: '0 auto',
    padding: 20,
  },
  title: {
    fontSize: 22,
    fontWeight: 700,
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 13,
    color: '#868e96',
    marginBottom: 16,
  },
  controls: {
    display: 'flex',
    gap: 12,
    marginBottom: 12,
    alignItems: 'center',
  },
  searchInput: {
    flex: 1,
    padding: '8px 12px',
    border: '1px solid #ced4da',
    borderRadius: 6,
    fontSize: 14,
  },
  sortBtn: {
    padding: '6px 12px',
    border: '1px solid #dee2e6',
    borderRadius: 6,
    cursor: 'pointer',
    fontSize: 12,
    background: '#f8f9fa',
  },
  sortBtnActive: {
    background: '#228be6',
    color: '#fff',
    borderColor: '#228be6',
  },
  grid: {
    border: '1px solid #dee2e6',
    borderRadius: 8,
    overflow: 'hidden',
  },
  headerRow: {
    display: 'flex',
    background: '#f1f3f5',
    borderBottom: '2px solid #dee2e6',
    fontWeight: 600,
    fontSize: 13,
    textTransform: 'uppercase' as const,
  },
  headerCell: {
    padding: '10px 12px',
    borderRight: '1px solid #e9ecef',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
    cursor: 'pointer',
    userSelect: 'none' as const,
  },
  viewport: {
    height: CONTAINER_HEIGHT,
    overflow: 'auto',
    position: 'relative' as const,
  },
  spacer: {
    position: 'relative' as const,
  },
  row: {
    display: 'flex',
    position: 'absolute' as const,
    width: '100%',
    borderBottom: '1px solid #f1f3f5',
    fontSize: 13,
    boxSizing: 'border-box' as const,
  },
  rowEven: {
    background: '#fafbfc',
  },
  cell: {
    padding: '10px 12px',
    borderRight: '1px solid #f1f3f5',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
  },
  info: {
    fontSize: 12,
    color: '#868e96',
    marginTop: 8,
  },
};

// ─── Mock data ───────────────────────────────────────────────────────────────

const COLUMNS: ColumnDef[] = [
  { key: 'id', header: 'ID', width: 80, sortable: true },
  { key: 'name', header: 'Name', width: 200, sortable: true },
  { key: 'email', header: 'Email', width: 250, sortable: true },
  { key: 'department', header: 'Department', width: 150, sortable: true },
  { key: 'salary', header: 'Salary', width: 120, sortable: true },
];

const DEPARTMENTS = ['Engineering', 'Marketing', 'Sales', 'HR', 'Finance', 'Operations', 'Legal', 'Support'];
const FIRST_NAMES = ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank', 'Grace', 'Hector', 'Ivy', 'Jack'];
const LAST_NAMES = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez'];

function generateMockData(count: number): DataRow[] {
  const rows: DataRow[] = [];
  for (let i = 0; i < count; i++) {
    const first = FIRST_NAMES[i % FIRST_NAMES.length];
    const last = LAST_NAMES[Math.floor(i / FIRST_NAMES.length) % LAST_NAMES.length];
    rows.push({
      id: i + 1,
      name: `${first} ${last}`,
      email: `${first.toLowerCase()}.${last.toLowerCase()}@example.com`,
      department: DEPARTMENTS[i % DEPARTMENTS.length],
      salary: 40000 + Math.floor(Math.random() * 80000),
    });
  }
  return rows;
}

const ALL_ROWS = generateMockData(TOTAL_ROWS);

// ─── Main Component ─────────────────────────────────────────────────────────

const DataGrid: React.FC = () => {
  const [filterText, setFilterText] = useState('');
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [scrollTop, setScrollTop] = useState(0);
  const viewportRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number>(0);

  // Filter
  const filteredRows = useMemo(() => {
    if (!filterText) return ALL_ROWS;
    const lower = filterText.toLowerCase();
    return ALL_ROWS.filter((row) =>
      Object.values(row).some((val) => String(val).toLowerCase().includes(lower)),
    );
  }, [filterText]);

  // Sort
  const sortedRows = useMemo(() => {
    if (!sortColumn) return filteredRows;
    const sorted = [...filteredRows].sort((a, b) => {
      const valA = a[sortColumn];
      const valB = b[sortColumn];
      let comparison = 0;
      if (typeof valA === 'number' && typeof valB === 'number') {
        comparison = valA - valB;
      } else {
        comparison = String(valA).localeCompare(String(valB));
      }
      return sortDirection === 'asc' ? comparison : -comparison;
    });
    return sorted;
  }, [filteredRows, sortColumn, sortDirection]);

  // Virtual scroll metrics
  const metrics: VirtualMetrics = useMemo(() => {
    const visibleCount = Math.ceil(CONTAINER_HEIGHT / ROW_HEIGHT);
    const totalHeight = sortedRows.length * ROW_HEIGHT;
    let start = Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN;
    if (start < 0) start = 0;
    let end = start + visibleCount + OVERSCAN * 2;
    if (end > sortedRows.length) end = sortedRows.length;
    return {
      startIndex: start,
      endIndex: end,
      visibleCount,
      totalHeight,
      offsetY: start * ROW_HEIGHT,
    };
  }, [scrollTop, sortedRows.length]);

  // Visible rows
  const visibleRows = useMemo(
    () => sortedRows.slice(metrics.startIndex, metrics.endIndex),
    [sortedRows, metrics.startIndex, metrics.endIndex],
  );

  // Scroll handler (throttled via rAF)
  const handleScroll = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => {
      if (viewportRef.current) {
        setScrollTop(viewportRef.current.scrollTop);
      }
    });
  }, []);

  useEffect(() => {
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  // Sort toggle
  const handleSort = useCallback(
    (key: string) => {
      if (sortColumn === key) {
        setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
      } else {
        setSortColumn(key);
        setSortDirection('asc');
      }
    },
    [sortColumn],
  );

  const sortIndicator = (key: string): string => {
    if (sortColumn !== key) return '';
    return sortDirection === 'asc' ? ' ▲' : ' ▼';
  };

  return (
    <div style={css.wrapper}>
      <div style={css.title}>Virtual Scroll Data Grid</div>
      <div style={css.subtitle}>
        {sortedRows.length.toLocaleString()} rows · Rendering {visibleRows.length} visible
      </div>

      {/* Controls */}
      <div style={css.controls}>
        <input
          style={css.searchInput}
          placeholder="Search all columns..."
          value={filterText}
          onChange={(e) => {
            setFilterText(e.target.value);
            setScrollTop(0);
            if (viewportRef.current) viewportRef.current.scrollTop = 0;
          }}
        />
        {COLUMNS.filter((c) => c.sortable).map((col) => (
          <button
            key={col.key}
            style={{
              ...css.sortBtn,
              ...(sortColumn === col.key ? css.sortBtnActive : {}),
            }}
            onClick={() => handleSort(col.key)}
          >
            {col.header}{sortIndicator(col.key)}
          </button>
        ))}
      </div>

      {/* Grid */}
      <div style={css.grid}>
        {/* Header */}
        <div style={css.headerRow}>
          {COLUMNS.map((col) => (
            <div
              key={col.key}
              style={{ ...css.headerCell, width: col.width, flexShrink: 0 }}
              onClick={() => col.sortable && handleSort(col.key)}
            >
              {col.header}{sortIndicator(col.key)}
            </div>
          ))}
        </div>

        {/* Viewport */}
        <div style={css.viewport} ref={viewportRef} onScroll={handleScroll}>
          <div style={{ ...css.spacer, height: metrics.totalHeight }}>
            {visibleRows.map((row, i) => {
              const absoluteIndex = metrics.startIndex + i;
              return (
                <div
                  key={String(row.id)}
                  style={{
                    ...css.row,
                    top: absoluteIndex * ROW_HEIGHT,
                    height: ROW_HEIGHT,
                    ...(absoluteIndex % 2 === 0 ? css.rowEven : {}),
                  }}
                >
                  {COLUMNS.map((col) => (
                    <div
                      key={col.key}
                      style={{ ...css.cell, width: col.width, flexShrink: 0 }}
                    >
                      {col.key === 'salary'
                        ? `$${Number(row[col.key]).toLocaleString()}`
                        : String(row[col.key] ?? '')}
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div style={css.info}>
        Scroll position: {Math.round(scrollTop)}px · Rows {metrics.startIndex + 1}–{metrics.endIndex} of{' '}
        {sortedRows.length.toLocaleString()}
      </div>
    </div>
  );
};

export default DataGrid;
