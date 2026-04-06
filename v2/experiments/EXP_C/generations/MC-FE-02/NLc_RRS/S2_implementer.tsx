import React, { useRef, useState, useMemo, useCallback, memo } from 'react';

// ── Types ──

interface RowData {
  id: number;
  name: string;
  email: string;
  age: number;
  city: string;
  score: number;
}

interface SortConfig {
  column: keyof RowData | null;
  direction: 'asc' | 'desc' | null;
}

// ── Constants ──

const ROW_HEIGHT = 36;
const VIEWPORT_HEIGHT = 600;
const OVERSCAN = 5;
const TOTAL_ROWS = 10000;

const CITIES = [
  'New York', 'London', 'Tokyo', 'Paris', 'Berlin',
  'Sydney', 'Toronto', 'Mumbai', 'Beijing', 'Seoul',
  'Moscow', 'Dubai', 'Singapore', 'Bangkok', 'Rome',
];

const COLUMNS: { key: keyof RowData; label: string; width: number; sortable: boolean }[] = [
  { key: 'id', label: 'ID', width: 80, sortable: false },
  { key: 'name', label: 'Name', width: 200, sortable: true },
  { key: 'email', label: 'Email', width: 280, sortable: false },
  { key: 'age', label: 'Age', width: 80, sortable: true },
  { key: 'city', label: 'City', width: 150, sortable: false },
  { key: 'score', label: 'Score', width: 100, sortable: true },
];

// ── Mock Data Generator ──

function generateData(count: number): RowData[] {
  const data: RowData[] = [];
  for (let i = 0; i < count; i++) {
    data.push({
      id: i + 1,
      name: `User ${i + 1}`,
      email: `user${i + 1}@example.com`,
      age: 18 + (i % 50),
      city: CITIES[i % CITIES.length],
      score: Math.round(((i * 7 + 13) % 100) * 10) / 10,
    });
  }
  return data;
}

// ── Styles ──

const css = {
  container: {
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    maxWidth: 960,
    margin: '0 auto',
    padding: 20,
    background: '#f8f9fa',
    minHeight: '100vh',
  } as React.CSSProperties,
  title: {
    textAlign: 'center' as const,
    fontSize: 22,
    fontWeight: 700,
    marginBottom: 16,
    color: '#2d3436',
  } as React.CSSProperties,
  filterBar: {
    marginBottom: 12,
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  } as React.CSSProperties,
  filterInput: {
    padding: '8px 12px',
    borderRadius: 6,
    border: '1px solid #ddd',
    fontSize: 14,
    width: 300,
    outline: 'none',
  } as React.CSSProperties,
  filterLabel: {
    fontSize: 14,
    color: '#636e72',
  } as React.CSSProperties,
  stats: {
    fontSize: 12,
    color: '#b2bec3',
    marginLeft: 'auto',
  } as React.CSSProperties,
  headerRow: {
    display: 'flex',
    background: '#2d3436',
    color: '#fff',
    fontWeight: 600,
    fontSize: 13,
    borderRadius: '6px 6px 0 0',
  } as React.CSSProperties,
  headerCell: {
    padding: '10px 12px',
    borderRight: '1px solid #636e72',
    cursor: 'default',
    userSelect: 'none' as const,
    display: 'flex',
    alignItems: 'center',
    gap: 4,
  } as React.CSSProperties,
  headerCellSortable: {
    cursor: 'pointer',
  } as React.CSSProperties,
  viewport: {
    height: VIEWPORT_HEIGHT,
    overflowY: 'auto' as const,
    border: '1px solid #ddd',
    borderTop: 'none',
    borderRadius: '0 0 6px 6px',
    background: '#fff',
    position: 'relative' as const,
  } as React.CSSProperties,
  row: {
    display: 'flex',
    position: 'absolute' as const,
    width: '100%',
    borderBottom: '1px solid #f0f0f0',
    fontSize: 13,
    transition: 'background 0.1s',
  } as React.CSSProperties,
  rowEven: {
    background: '#fafafa',
  } as React.CSSProperties,
  cell: {
    padding: '8px 12px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
  } as React.CSSProperties,
  sortArrow: {
    fontSize: 10,
    marginLeft: 2,
  } as React.CSSProperties,
};

// ── GridRow (memoized) ──

const GridRow = memo<{
  row: RowData;
  index: number;
  top: number;
}>(({ row, index, top }) => (
  <div
    style={{
      ...css.row,
      top,
      ...(index % 2 === 0 ? css.rowEven : {}),
    }}
  >
    {COLUMNS.map((col) => (
      <div key={col.key} style={{ ...css.cell, width: col.width, flexShrink: 0 }}>
        {String(row[col.key])}
      </div>
    ))}
  </div>
));

GridRow.displayName = 'GridRow';

// ── FilterBar ──

const FilterBar: React.FC<{
  value: string;
  onChange: (v: string) => void;
  total: number;
  filtered: number;
}> = ({ value, onChange, total, filtered }) => (
  <div style={css.filterBar}>
    <span style={css.filterLabel}>Filter:</span>
    <input
      style={css.filterInput}
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder="Search by name or email..."
    />
    <span style={css.stats}>
      {filtered === total
        ? `${total.toLocaleString()} rows`
        : `${filtered.toLocaleString()} / ${total.toLocaleString()} rows`}
    </span>
  </div>
);

// ── GridHeader ──

const GridHeader: React.FC<{
  sort: SortConfig;
  onSort: (column: keyof RowData) => void;
}> = ({ sort, onSort }) => {
  const getSortIndicator = (col: keyof RowData): string => {
    if (sort.column !== col) return '';
    return sort.direction === 'asc' ? ' ▲' : ' ▼';
  };

  return (
    <div style={css.headerRow}>
      {COLUMNS.map((col) => (
        <div
          key={col.key}
          style={{
            ...css.headerCell,
            width: col.width,
            flexShrink: 0,
            ...(col.sortable ? css.headerCellSortable : {}),
          }}
          onClick={() => col.sortable && onSort(col.key)}
        >
          {col.label}
          {col.sortable && (
            <span style={css.sortArrow}>{getSortIndicator(col.key)}</span>
          )}
        </div>
      ))}
    </div>
  );
};

// ── DataGrid (root) ──

const DataGrid: React.FC = () => {
  const rawDataRef = useRef<RowData[]>(generateData(TOTAL_ROWS));
  const scrollRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [filter, setFilter] = useState('');
  const [sort, setSort] = useState<SortConfig>({ column: null, direction: null });
  const rafRef = useRef<number | null>(null);

  const filteredData = useMemo(() => {
    if (!filter.trim()) return rawDataRef.current;
    const lower = filter.toLowerCase();
    return rawDataRef.current.filter(
      (row) =>
        row.name.toLowerCase().includes(lower) ||
        row.email.toLowerCase().includes(lower)
    );
  }, [filter]);

  const sortedData = useMemo(() => {
    if (!sort.column || !sort.direction) return filteredData;
    const col = sort.column;
    const dir = sort.direction === 'asc' ? 1 : -1;
    return [...filteredData].sort((a, b) => {
      const va = a[col];
      const vb = b[col];
      if (typeof va === 'string' && typeof vb === 'string') {
        return va.localeCompare(vb) * dir;
      }
      return ((va as number) - (vb as number)) * dir;
    });
  }, [filteredData, sort]);

  const totalRows = sortedData.length;
  const totalHeight = totalRows * ROW_HEIGHT;

  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const endIndex = Math.min(
    totalRows - 1,
    Math.ceil((scrollTop + VIEWPORT_HEIGHT) / ROW_HEIGHT) + OVERSCAN
  );

  const visibleRows = sortedData.slice(startIndex, endIndex + 1);

  const handleScroll = useCallback(() => {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => {
      if (scrollRef.current) {
        setScrollTop(scrollRef.current.scrollTop);
      }
    });
  }, []);

  const handleSort = useCallback(
    (column: keyof RowData) => {
      setSort((prev) => {
        if (prev.column !== column) return { column, direction: 'asc' };
        if (prev.direction === 'asc') return { column, direction: 'desc' };
        return { column: null, direction: null };
      });
    },
    []
  );

  return (
    <div style={css.container}>
      <div style={css.title}>Virtual Scroll Data Grid</div>
      <FilterBar
        value={filter}
        onChange={setFilter}
        total={TOTAL_ROWS}
        filtered={totalRows}
      />
      <GridHeader sort={sort} onSort={handleSort} />
      <div
        ref={scrollRef}
        style={css.viewport}
        onScroll={handleScroll}
      >
        <div style={{ height: totalHeight, position: 'relative', willChange: 'transform' }}>
          {visibleRows.map((row, i) => {
            const actualIndex = startIndex + i;
            return (
              <GridRow
                key={row.id}
                row={row}
                index={actualIndex}
                top={actualIndex * ROW_HEIGHT}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default DataGrid;
