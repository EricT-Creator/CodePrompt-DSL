import React, { useRef, useState, useEffect, useCallback, useMemo } from 'react';

// ── Types ──────────────────────────────────────────────────────────────

interface DataRow {
  id: number;
  name: string;
  email: string;
  age: number;
  salary: number;
  department: string;
  joinDate: string;
  city: string;
}

interface ColumnDef {
  id: keyof DataRow;
  title: string;
  width: number;
  sortable: boolean;
}

type SortDirection = 'asc' | 'desc' | null;

// ── CSS ────────────────────────────────────────────────────────────────

const css = `
.grid-container{font-family:system-ui,-apple-system,sans-serif;display:flex;flex-direction:column;height:100vh;background:#f8fafc}
.grid-toolbar{display:flex;align-items:center;gap:12px;padding:12px 16px;background:#fff;border-bottom:1px solid #e2e8f0}
.grid-toolbar input{flex:1;padding:8px 12px;border:1px solid #d1d5db;border-radius:6px;font-size:14px;outline:none}
.grid-toolbar input:focus{border-color:#3b82f6;box-shadow:0 0 0 2px rgba(59,130,246,.15)}
.grid-stats{font-size:13px;color:#64748b;white-space:nowrap}
.grid-wrapper{flex:1;overflow:hidden;position:relative;background:#fff;margin:0 16px 16px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.grid-header-row{display:flex;background:#f1f5f9;border-bottom:2px solid #e2e8f0;position:sticky;top:0;z-index:2}
.grid-header-cell{padding:10px 12px;font-weight:600;font-size:13px;color:#475569;cursor:pointer;user-select:none;border-right:1px solid #e2e8f0;display:flex;align-items:center;gap:4px;flex-shrink:0}
.grid-header-cell:hover{background:#e2e8f0}
.sort-indicator{font-size:11px}
.grid-body{overflow-y:auto;position:relative}
.grid-row{display:flex;border-bottom:1px solid #f1f5f9;transition:background .1s}
.grid-row:hover{background:#f8fafc}
.grid-row-even{background:#fafbfc}
.grid-cell{padding:8px 12px;font-size:13px;color:#334155;border-right:1px solid #f1f5f9;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex-shrink:0}
.grid-empty{padding:40px;text-align:center;color:#94a3b8;font-size:14px}
`;

// ── Mock data generator ────────────────────────────────────────────────

const DEPARTMENTS = ['Engineering', 'Marketing', 'Sales', 'HR', 'Finance', 'Design', 'Product', 'Legal'];
const CITIES = ['New York', 'London', 'Tokyo', 'Berlin', 'Paris', 'Sydney', 'Toronto', 'Singapore'];
const FIRST_NAMES = ['Alice', 'Bob', 'Charlie', 'Diana', 'Ethan', 'Fiona', 'George', 'Helen', 'Ivan', 'Julia'];
const LAST_NAMES = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Wilson', 'Moore'];

function seededRandom(seed: number): () => number {
  let s = seed;
  return () => {
    s = (s * 16807 + 0) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

function generateMockData(count: number): DataRow[] {
  const rand = seededRandom(42);
  const rows: DataRow[] = [];
  for (let i = 0; i < count; i++) {
    const first = FIRST_NAMES[Math.floor(rand() * FIRST_NAMES.length)];
    const last = LAST_NAMES[Math.floor(rand() * LAST_NAMES.length)];
    rows.push({
      id: i + 1,
      name: `${first} ${last}`,
      email: `${first.toLowerCase()}.${last.toLowerCase()}${i}@example.com`,
      age: 22 + Math.floor(rand() * 40),
      salary: 40000 + Math.floor(rand() * 120000),
      department: DEPARTMENTS[Math.floor(rand() * DEPARTMENTS.length)],
      joinDate: `${2015 + Math.floor(rand() * 10)}-${String(1 + Math.floor(rand() * 12)).padStart(2, '0')}-${String(1 + Math.floor(rand() * 28)).padStart(2, '0')}`,
      city: CITIES[Math.floor(rand() * CITIES.length)],
    });
  }
  return rows;
}

// ── Columns config ─────────────────────────────────────────────────────

const COLUMNS: ColumnDef[] = [
  { id: 'id', title: 'ID', width: 70, sortable: true },
  { id: 'name', title: 'Name', width: 180, sortable: true },
  { id: 'email', title: 'Email', width: 260, sortable: true },
  { id: 'age', title: 'Age', width: 70, sortable: true },
  { id: 'salary', title: 'Salary', width: 110, sortable: true },
  { id: 'department', title: 'Department', width: 130, sortable: true },
  { id: 'joinDate', title: 'Join Date', width: 120, sortable: true },
  { id: 'city', title: 'City', width: 120, sortable: true },
];

const ROW_HEIGHT = 36;
const BUFFER_ROWS = 10;

// ── Component ──────────────────────────────────────────────────────────

const VirtualScrollGrid: React.FC = () => {
  const allData = useMemo(() => generateMockData(10000), []);

  const [searchTerm, setSearchTerm] = useState('');
  const [sortColumn, setSortColumn] = useState<keyof DataRow | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [containerHeight, setContainerHeight] = useState(600);

  const bodyRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number>(0);

  // Filter + sort
  const processedData = useMemo(() => {
    let data = allData;

    // Filter
    if (searchTerm.trim()) {
      const lower = searchTerm.toLowerCase();
      data = data.filter((row) =>
        Object.values(row).some((v) => String(v).toLowerCase().includes(lower)),
      );
    }

    // Sort
    if (sortColumn && sortDirection) {
      const dir = sortDirection === 'asc' ? 1 : -1;
      data = [...data].sort((a, b) => {
        const av = a[sortColumn];
        const bv = b[sortColumn];
        if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * dir;
        return String(av).localeCompare(String(bv)) * dir;
      });
    }

    return data;
  }, [allData, searchTerm, sortColumn, sortDirection]);

  // Virtual scroll calculation
  const visibleCount = Math.ceil(containerHeight / ROW_HEIGHT);
  const startIdx = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - BUFFER_ROWS);
  const endIdx = Math.min(processedData.length, Math.floor(scrollTop / ROW_HEIGHT) + visibleCount + BUFFER_ROWS);
  const visibleRows = processedData.slice(startIdx, endIdx);
  const totalHeight = processedData.length * ROW_HEIGHT;
  const offsetY = startIdx * ROW_HEIGHT;

  // Scroll handler with rAF throttle
  const handleScroll = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => {
      if (bodyRef.current) {
        setScrollTop(bodyRef.current.scrollTop);
      }
    });
  }, []);

  // Measure container
  useEffect(() => {
    const el = bodyRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerHeight(entry.contentRect.height);
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Debounced search
  const searchTimeout = useRef<ReturnType<typeof setTimeout>>();
  const [inputValue, setInputValue] = useState('');
  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setInputValue(val);
    if (searchTimeout.current) clearTimeout(searchTimeout.current);
    searchTimeout.current = setTimeout(() => setSearchTerm(val), 200);
  }, []);

  // Sort handler
  const handleSort = useCallback((colId: keyof DataRow) => {
    setSortColumn((prev) => {
      if (prev === colId) {
        setSortDirection((d) => (d === 'asc' ? 'desc' : d === 'desc' ? null : 'asc'));
        return colId;
      }
      setSortDirection('asc');
      return colId;
    });
  }, []);

  const totalWidth = COLUMNS.reduce((s, c) => s + c.width, 0);

  return (
    <>
      <style>{css}</style>
      <div className="grid-container">
        <div className="grid-toolbar">
          <input placeholder="Search all columns…" value={inputValue} onChange={handleSearchChange} />
          <div className="grid-stats">
            {processedData.length.toLocaleString()} / {allData.length.toLocaleString()} rows
          </div>
        </div>

        <div className="grid-wrapper">
          {/* Header */}
          <div className="grid-header-row" style={{ minWidth: totalWidth }}>
            {COLUMNS.map((col) => (
              <div
                key={col.id}
                className="grid-header-cell"
                style={{ width: col.width }}
                onClick={() => col.sortable && handleSort(col.id)}
              >
                {col.title}
                {sortColumn === col.id && sortDirection && (
                  <span className="sort-indicator">{sortDirection === 'asc' ? '▲' : '▼'}</span>
                )}
              </div>
            ))}
          </div>

          {/* Body */}
          <div
            ref={bodyRef}
            className="grid-body"
            style={{ height: 'calc(100% - 42px)', overflowY: 'auto' }}
            onScroll={handleScroll}
          >
            <div style={{ height: totalHeight, position: 'relative', minWidth: totalWidth }}>
              <div style={{ transform: `translateY(${offsetY}px)`, position: 'absolute', width: '100%' }}>
                {visibleRows.map((row, i) => {
                  const globalIdx = startIdx + i;
                  return (
                    <div
                      key={row.id}
                      className={`grid-row${globalIdx % 2 === 0 ? ' grid-row-even' : ''}`}
                      style={{ height: ROW_HEIGHT }}
                    >
                      {COLUMNS.map((col) => (
                        <div key={col.id} className="grid-cell" style={{ width: col.width, lineHeight: `${ROW_HEIGHT - 16}px` }}>
                          {col.id === 'salary' ? `$${(row[col.id] as number).toLocaleString()}` : String(row[col.id])}
                        </div>
                      ))}
                    </div>
                  );
                })}
              </div>
            </div>
            {processedData.length === 0 && <div className="grid-empty">No matching records found</div>}
          </div>
        </div>
      </div>
    </>
  );
};

export default VirtualScrollGrid;
