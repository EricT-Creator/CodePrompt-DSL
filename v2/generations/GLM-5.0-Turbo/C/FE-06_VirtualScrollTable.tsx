import React, { useState, useRef, useMemo, useCallback } from 'react';

/* ========== CSS Module (comment block) ==========
.module_wrapper {
  --header-h: 44px;
  --row-h: 36px;
  --border: #e2e8f0;
  --header-bg: #f8fafc;
  --hover-bg: #f1f5f9;
  --text: #334155;
  --text-muted: #64748b;
  --accent: #3b82f6;
}
.module_wrapper { width: 100%; max-width: 800px; margin: 40px auto; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; border: 1px solid var(--border); border-radius: 10px; overflow: hidden; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.module_headerRow { display: grid; grid-template-columns: 80px 1fr 120px 120px 140px; height: var(--header-h); align-items: center; background: var(--header-bg); border-bottom: 2px solid var(--border); font-weight: 600; font-size: 13px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; padding: 0 16px; user-select: none; }
.module_sortable { cursor: pointer; display: flex; align-items: center; gap: 4px; }
.module_sortable:hover { color: var(--accent); }
.module_body { height: 500px; overflow-y: auto; position: relative; }
.module_row { display: grid; grid-template-columns: 80px 1fr 120px 120px 140px; height: var(--row-h); align-items: center; padding: 0 16px; font-size: 14px; color: var(--text); border-bottom: 1px solid #f1f5f9; }
.module_row:hover { background: var(--hover-bg); }
.module_rowId { color: var(--text-muted); font-size: 13px; }
.module_title { margin: 0; padding: 20px 16px 12px; font-size: 20px; font-weight: 700; color: #1e293b; }
.module_subtitle { margin: 0; padding: 0 16px 16px; font-size: 13px; color: var(--text-muted); }
========= end CSS Module ========== */

interface Row {
  id: number;
  name: string;
  email: string;
  department: string;
  salary: number;
}

type SortKey = 'name' | 'department' | 'salary';
type SortDir = 'asc' | 'desc';

const OVERSCAN = 5;
const ROW_HEIGHT = 36;
const VISIBLE_HEIGHT = 500;
const TOTAL_ROWS = 10000;

const departments = ['Engineering', 'Marketing', 'Sales', 'HR', 'Finance', 'Design', 'Operations', 'Legal'];
const firstNames = ['James','Mary','Robert','Patricia','John','Jennifer','Michael','Linda','David','Elizabeth','William','Barbara','Richard','Susan','Joseph','Jessica','Thomas','Sarah','Christopher','Karen','Daniel','Nancy','Matthew','Lisa','Anthony','Betty','Mark','Margaret','Steven','Sandra'];
const lastNames = ['Smith','Johnson','Williams','Brown','Jones','Garcia','Miller','Davis','Rodriguez','Martinez','Hernandez','Lopez','Gonzalez','Wilson','Anderson','Thomas','Taylor','Moore','Jackson','Martin'];

function seededRandom(seed: number): () => number {
  let s = seed;
  return () => {
    s = (s * 16807) % 2147483647;
    return s / 2147483647;
  };
}

function generateData(count: number): Row[] {
  const rng = seededRandom(42);
  const rows: Row[] = [];
  for (let i = 1; i <= count; i++) {
    const fn = firstNames[Math.floor(rng() * firstNames.length)];
    const ln = lastNames[Math.floor(rng() * lastNames.length)];
    const dept = departments[Math.floor(rng() * departments.length)];
    const salary = Math.floor(rng() * 180000) + 30000;
    rows.push({
      id: i,
      name: `${fn} ${ln}`,
      email: `${fn.toLowerCase()}.${ln.toLowerCase()}${i}@example.com`,
      department: dept,
      salary,
    });
  }
  return rows;
}

function sortData(data: Row[], key: SortKey, dir: SortDir): Row[] {
  return [...data].sort((a, b) => {
    const aVal = a[key];
    const bVal = b[key];
    let cmp: number;
    if (typeof aVal === 'string' && typeof bVal === 'string') {
      cmp = aVal.localeCompare(bVal);
    } else {
      cmp = (aVal as number) - (bVal as number);
    }
    return dir === 'asc' ? cmp : -cmp;
  });
}

export default function VirtualScrollTable() {
  const [allData] = useState<Row[]>(() => generateData(TOTAL_ROWS));
  const [sortKey, setSortKey] = useState<SortKey>('name');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [scrollTop, setScrollTop] = useState(0);
  const bodyRef = useRef<HTMLDivElement>(null);

  const sortedData = useMemo(
    () => sortData(allData, sortKey, sortDir),
    [allData, sortKey, sortDir]
  );

  const handleSort = useCallback(
    (key: SortKey) => {
      if (sortKey === key) {
        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
      } else {
        setSortKey(key);
        setSortDir('asc');
      }
    },
    [sortKey]
  );

  const handleScroll = useCallback(() => {
    if (bodyRef.current) {
      setScrollTop(bodyRef.current.scrollTop);
    }
  }, []);

  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const endIndex = Math.min(
    sortedData.length - 1,
    Math.ceil((scrollTop + VISIBLE_HEIGHT) / ROW_HEIGHT) + OVERSCAN
  );

  const visibleRows = sortedData.slice(startIndex, endIndex + 1);
  const totalHeight = sortedData.length * ROW_HEIGHT;
  const offsetY = startIndex * ROW_HEIGHT;

  const formatSalary = (v: number) => '$' + v.toLocaleString('en-US');

  const sortIcon = (key: SortKey) => {
    if (sortKey !== key) return ' ↕';
    return sortDir === 'asc' ? ' ↑' : ' ↓';
  };

  return (
    <div style={wrapperStyle}>
      <p style={titleStyle}>Virtual Scroll Table</p>
      <p style={subtitleStyle}>
        {TOTAL_ROWS.toLocaleString()} rows · sorted by {sortKey} ({sortDir}) · rendering {startIndex + 1}–{endIndex + 1}
      </p>
      <div style={headerRowStyle}>
        <span style={colStyle}>#</span>
        <span style={{ ...colStyle, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }} onClick={() => handleSort('name')}>
          Name{sortIcon('name')}
        </span>
        <span style={colStyle}>Email</span>
        <span style={{ ...colStyle, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }} onClick={() => handleSort('department')}>
          Dept{sortIcon('department')}
        </span>
        <span style={{ ...colStyle, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }} onClick={() => handleSort('salary')}>
          Salary{sortIcon('salary')}
        </span>
      </div>
      <div ref={bodyRef} style={bodyStyle} onScroll={handleScroll}>
        <div style={{ height: totalHeight, position: 'relative' }}>
          <div style={{ transform: `translateY(${offsetY}px)` }}>
            {visibleRows.map((row) => (
              <div key={row.id} style={rowStyle}>
                <span style={{ ...colStyle, color: '#64748b', fontSize: 13 }}>{row.id}</span>
                <span style={{ ...colStyle, fontWeight: 500 }}>{row.name}</span>
                <span style={{ ...colStyle, fontSize: 13, color: '#64748b' }}>{row.email}</span>
                <span style={colStyle}>{row.department}</span>
                <span style={colStyle}>{formatSalary(row.salary)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

const wrapperStyle: React.CSSProperties = {
  width: '100%', maxWidth: 800, margin: '40px auto',
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  border: '1px solid #e2e8f0', borderRadius: 10, overflow: 'hidden',
  background: '#fff', boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
};
const titleStyle: React.CSSProperties = { margin: 0, padding: '20px 16px 4px', fontSize: 20, fontWeight: 700, color: '#1e293b' };
const subtitleStyle: React.CSSProperties = { margin: 0, padding: '0 16px 16px', fontSize: 13, color: '#64748b' };
const headerRowStyle: React.CSSProperties = {
  display: 'grid', gridTemplateColumns: '80px 1fr 120px 120px 140px',
  height: 44, alignItems: 'center', background: '#f8fafc',
  borderBottom: '2px solid #e2e8f0', fontWeight: 600, fontSize: 13,
  color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px', padding: '0 16px',
  userSelect: 'none',
};
const bodyStyle: React.CSSProperties = { height: VISIBLE_HEIGHT, overflowY: 'auto', position: 'relative' };
const rowStyle: React.CSSProperties = {
  display: 'grid', gridTemplateColumns: '80px 1fr 120px 120px 140px',
  height: ROW_HEIGHT, alignItems: 'center', padding: '0 16px',
  fontSize: 14, color: '#334155', borderBottom: '1px solid #f1f5f9',
};
const colStyle: React.CSSProperties = { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' };
