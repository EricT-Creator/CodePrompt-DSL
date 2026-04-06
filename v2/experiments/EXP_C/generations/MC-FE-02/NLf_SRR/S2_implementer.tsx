import React, { useRef, useState, useEffect, useCallback, useMemo } from "react";

// ── Inline CSS (CSS Modules substitute for single file) ───────────────
const css = `
  .grid { font-family:system-ui,sans-serif; background:#fff; border:1px solid #e0e0e0; border-radius:8px; overflow:hidden; display:flex; flex-direction:column; height:80vh; margin:24px; }
  .search { padding:12px 16px; border-bottom:1px solid #e0e0e0; display:flex; align-items:center; gap:8px; }
  .searchInput { flex:1; padding:8px 12px; border:1px solid #ddd; border-radius:6px; font-size:13px; outline:none; }
  .searchInput:focus { border-color:#4a90d9; }
  .stats { font-size:12px; color:#888; white-space:nowrap; }
  .headerRow { display:flex; border-bottom:2px solid #e0e0e0; background:#fafafa; position:sticky; top:0; z-index:2; }
  .headerCell { padding:10px 12px; font-size:13px; font-weight:700; color:#444; cursor:pointer; user-select:none; display:flex; align-items:center; gap:4px; border-right:1px solid #eee; flex-shrink:0; }
  .headerCell:hover { background:#f0f0f0; }
  .sortArrow { font-size:10px; color:#999; }
  .scrollContainer { flex:1; overflow-y:auto; position:relative; }
  .innerContainer { position:relative; }
  .row { display:flex; position:absolute; left:0; right:0; border-bottom:1px solid #f0f0f0; }
  .rowEven { background:#fff; }
  .rowOdd { background:#fafbfc; }
  .row:hover { background:#e8f0fe; }
  .cell { padding:8px 12px; font-size:13px; color:#333; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; border-right:1px solid #f0f0f0; flex-shrink:0; }
`;

// ── Types ──────────────────────────────────────────────────────────────
interface DataItem {
  id: number;
  name: string;
  email: string;
  age: number;
  city: string;
  salary: number;
  department: string;
}

interface ColumnDef {
  key: keyof DataItem;
  label: string;
  width: number;
  sortable: boolean;
}

// ── Mock Data ──────────────────────────────────────────────────────────
const FIRST_NAMES = ["Alice","Bob","Carol","Dave","Eve","Frank","Grace","Hank","Ivy","Jack","Kate","Leo","Mia","Nick","Olive","Pat","Quinn","Rose","Sam","Tina","Uma","Vic","Wendy","Xander","Yara","Zane"];
const LAST_NAMES = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez","Martinez","Hernandez","Lopez","Gonzalez","Wilson","Anderson","Thomas","Taylor","Moore","Jackson","Martin"];
const CITIES = ["New York","Los Angeles","Chicago","Houston","Phoenix","Philadelphia","San Antonio","San Diego","Dallas","Austin","Denver","Boston","Seattle","Atlanta","Miami","Portland","Minneapolis","Detroit","Cleveland","Tampa"];
const DEPTS = ["Engineering","Marketing","Sales","Design","Finance","HR","Legal","Operations","Support","Research"];

function generateData(count: number): DataItem[] {
  const data: DataItem[] = [];
  for (let i = 0; i < count; i++) {
    const first = FIRST_NAMES[i % FIRST_NAMES.length];
    const last = LAST_NAMES[i % LAST_NAMES.length];
    data.push({
      id: i + 1,
      name: `${first} ${last}`,
      email: `${first.toLowerCase()}.${last.toLowerCase()}${i}@example.com`,
      age: 22 + (i * 7) % 40,
      city: CITIES[i % CITIES.length],
      salary: 40000 + ((i * 137) % 100) * 1000,
      department: DEPTS[i % DEPTS.length],
    });
  }
  return data;
}

const ALL_DATA = generateData(10000);

const COLUMNS: ColumnDef[] = [
  { key: "id", label: "ID", width: 70, sortable: true },
  { key: "name", label: "Name", width: 180, sortable: true },
  { key: "email", label: "Email", width: 260, sortable: true },
  { key: "age", label: "Age", width: 70, sortable: true },
  { key: "city", label: "City", width: 140, sortable: true },
  { key: "salary", label: "Salary", width: 110, sortable: true },
  { key: "department", label: "Dept", width: 130, sortable: true },
];

const ROW_HEIGHT = 36;
const OVERSCAN = 5;

// ── GridHeader ─────────────────────────────────────────────────────────
function GridHeader({
  columns,
  sortKey,
  sortDir,
  onSort,
}: {
  columns: ColumnDef[];
  sortKey: string | null;
  sortDir: "asc" | "desc" | null;
  onSort: (key: string) => void;
}) {
  return (
    <div className="headerRow">
      {columns.map((c) => (
        <div key={c.key} className="headerCell" style={{ width: c.width }} onClick={() => c.sortable && onSort(c.key)}>
          {c.label}
          {sortKey === c.key && <span className="sortArrow">{sortDir === "asc" ? "▲" : "▼"}</span>}
        </div>
      ))}
    </div>
  );
}

// ── GridRow ─────────────────────────────────────────────────────────────
const GridRow = React.memo(function GridRow({
  item,
  columns,
  style,
  even,
}: {
  item: DataItem;
  columns: ColumnDef[];
  style: React.CSSProperties;
  even: boolean;
}) {
  return (
    <div className={`row ${even ? "rowEven" : "rowOdd"}`} style={style}>
      {columns.map((c) => (
        <div key={c.key} className="cell" style={{ width: c.width }}>
          {c.key === "salary" ? `$${(item[c.key] as number).toLocaleString()}` : String(item[c.key])}
        </div>
      ))}
    </div>
  );
});

// ── Main Component ─────────────────────────────────────────────────────
export default function VirtualDataGrid() {
  const [searchTerm, setSearchTerm] = useState("");
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc" | null>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [containerHeight, setContainerHeight] = useState(600);
  const scrollRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number>(0);

  const filteredData = useMemo(() => {
    let data = ALL_DATA;
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      data = data.filter((item) =>
        Object.values(item).some((v) => String(v).toLowerCase().includes(term))
      );
    }
    if (sortKey && sortDir) {
      const dir = sortDir === "asc" ? 1 : -1;
      data = [...data].sort((a, b) => {
        const va = a[sortKey as keyof DataItem];
        const vb = b[sortKey as keyof DataItem];
        if (typeof va === "number" && typeof vb === "number") return (va - vb) * dir;
        return String(va).localeCompare(String(vb)) * dir;
      });
    }
    return data;
  }, [searchTerm, sortKey, sortDir]);

  const totalHeight = filteredData.length * ROW_HEIGHT;
  const visibleCount = Math.ceil(containerHeight / ROW_HEIGHT);
  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const endIndex = Math.min(filteredData.length, startIndex + visibleCount + OVERSCAN * 2);
  const visibleItems = filteredData.slice(startIndex, endIndex);

  const handleScroll = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => {
      if (scrollRef.current) setScrollTop(scrollRef.current.scrollTop);
    });
  }, []);

  const handleSort = useCallback((key: string) => {
    setSortKey((prev) => {
      if (prev === key) {
        setSortDir((d) => (d === "asc" ? "desc" : d === "desc" ? null : "asc"));
        if (sortDir === "desc") return null;
        return key;
      }
      setSortDir("asc");
      return key;
    });
  }, [sortDir]);

  useEffect(() => {
    const measure = () => {
      if (scrollRef.current) setContainerHeight(scrollRef.current.clientHeight);
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);

  return (
    <>
      <style>{css}</style>
      <div className="grid">
        <div className="search">
          <input
            className="searchInput"
            placeholder="Search all columns…"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <span className="stats">{filteredData.length.toLocaleString()} rows</span>
        </div>
        <GridHeader columns={COLUMNS} sortKey={sortKey} sortDir={sortDir} onSort={handleSort} />
        <div className="scrollContainer" ref={scrollRef} onScroll={handleScroll}>
          <div className="innerContainer" style={{ height: totalHeight }}>
            {visibleItems.map((item, i) => {
              const idx = startIndex + i;
              return (
                <GridRow
                  key={item.id}
                  item={item}
                  columns={COLUMNS}
                  even={idx % 2 === 0}
                  style={{
                    top: idx * ROW_HEIGHT,
                    height: ROW_HEIGHT,
                    willChange: "transform",
                  }}
                />
              );
            })}
          </div>
        </div>
      </div>
    </>
  );
}
