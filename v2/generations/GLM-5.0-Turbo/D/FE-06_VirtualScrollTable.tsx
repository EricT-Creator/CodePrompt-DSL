import React, { useRef, useState, useCallback, useMemo, useEffect } from 'react';

/*
 * ===== CSS Module 内容 (注释块) =====
 */

const cssModuleContent = `
/* ===== VirtualScrollTable.module.css ===== */

.vst-wrapper {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  max-width: 800px;
  margin: 40px auto;
  padding: 0 16px;
}

.vst-title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 4px;
  color: #1a1a1a;
}

.vst-subtitle {
  font-size: 13px;
  color: #888;
  margin-bottom: 16px;
}

.vst-container {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}

.vst-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.vst-thead {
  position: sticky;
  top: 0;
  z-index: 10;
}

.vst-header-row {
  background: #f5f7fa;
  border-bottom: 2px solid #d0d5dd;
}

.vst-th {
  padding: 12px 16px;
  text-align: left;
  font-weight: 600;
  font-size: 13px;
  color: #555;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s ease;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.vst-th:hover {
  background: #e8ecf0;
}

.vst-th-sorted-asc::after {
  content: " \\25B2";
  color: #4a90d9;
}

.vst-th-sorted-desc::after {
  content: " \\25BC";
  color: #4a90d9;
}

.vst-th-id { width: 80px; }
.vst-th-name { width: auto; }
.vst-th-value { width: 120px; text-align: right; }

.vst-scroll-area {
  max-height: 600px;
  overflow-y: auto;
  overflow-x: hidden;
}

.vst-scroll-spacer {
  position: relative;
}

.vst-row {
  position: absolute;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.1s ease;
}

.vst-row:hover {
  background: #f8fafc;
}

.vst-row-even {
  background: #fafbfc;
}

.vst-row-even:hover {
  background: #f0f4f8;
}

.vst-cell {
  padding: 10px 16px;
  font-size: 14px;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex-shrink: 0;
}

.vst-cell-id {
  width: 80px;
  color: #888;
  font-size: 13px;
}

.vst-cell-name {
  flex: 1;
  min-width: 0;
}

.vst-cell-value {
  width: 120px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.vst-info {
  margin-top: 12px;
  font-size: 13px;
  color: #888;
}
`;

function injectStyles(css: string) {
  const id = 'vst-injected-styles';
  if (document.getElementById(id)) return;
  const el = document.createElement('style');
  el.id = id;
  el.textContent = css;
  document.head.appendChild(el);
}

interface RowData {
  id: number;
  name: string;
  value: number;
}

type SortKey = 'id' | 'name' | 'value';
type SortDir = 'asc' | 'desc';

const TOTAL_ROWS = 100000;
const ROW_HEIGHT = 40;
const BUFFER_SIZE = 10;

function generateData(count: number): RowData[] {
  const firstNames = ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank', 'Grace', 'Hank', 'Ivy', 'Jack', 'Kate', 'Leo', 'Mona', 'Nick', 'Olga', 'Paul'];
  const data: RowData[] = [];
  for (let i = 0; i < count; i++) {
    data.push({
      id: i + 1,
      name: `${firstNames[i % firstNames.length]}_${Math.floor(i / firstNames.length) + 1}`,
      value: Math.round(Math.random() * 10000) / 100,
    });
  }
  return data;
}

const VirtualScrollTable: React.FC = () => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [sortKey, setSortKey] = useState<SortKey>('id');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [scrollTop, setScrollTop] = useState(0);

  const allData = useMemo(() => generateData(TOTAL_ROWS), []);

  const sortedData = useMemo(() => {
    const arr = [...allData];
    arr.sort((a, b) => {
      let cmp = 0;
      if (sortKey === 'id') cmp = a.id - b.id;
      else if (sortKey === 'name') cmp = a.name.localeCompare(b.name);
      else cmp = a.value - b.value;
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return arr;
  }, [allData, sortKey, sortDir]);

  const handleSort = useCallback((key: SortKey) => {
    if (key === sortKey) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  }, [sortKey]);

  const handleScroll = useCallback(() => {
    if (scrollRef.current) {
      setScrollTop(scrollRef.current.scrollTop);
    }
  }, []);

  const { visibleStart, visibleEnd } = useMemo(() => {
    const start = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - BUFFER_SIZE);
    const containerHeight = 600;
    const visibleCount = Math.ceil(containerHeight / ROW_HEIGHT) + BUFFER_SIZE * 2;
    const end = Math.min(sortedData.length, start + visibleCount);
    return { visibleStart: start, visibleEnd: end };
  }, [scrollTop, sortedData.length]);

  const visibleData = sortedData.slice(visibleStart, visibleEnd);

  useEffect(() => {
    injectStyles(cssModuleContent);
  }, []);

  const getThClass = (key: SortKey) => {
    if (sortKey !== key) return 'vst-th';
    return `vst-th vst-th-sorted-${sortDir}`;
  };

  return (
    <div className="vst-wrapper">
      <h2 className="vst-title">虚拟滚动表格</h2>
      <p className="vst-subtitle">{TOTAL_ROWS.toLocaleString()} 行数据 · 仅渲染可见行</p>

      <div className="vst-container">
        <table className="vst-table">
          <thead className="vst-thead">
            <tr className="vst-header-row">
              <th className={`${getThClass('id')} vst-th-id`} onClick={() => handleSort('id')}>ID</th>
              <th className={`${getThClass('name')} vst-th-name`} onClick={() => handleSort('name')}>名称</th>
              <th className={`${getThClass('value')} vst-th-value`} onClick={() => handleSort('value')}>数值</th>
            </tr>
          </thead>
        </table>

        <div className="vst-scroll-area" ref={scrollRef} onScroll={handleScroll}>
          <div className="vst-scroll-spacer" style={{ height: sortedData.length * ROW_HEIGHT }}>
            {visibleData.map((row, idx) => {
              const globalIdx = visibleStart + idx;
              const isEven = globalIdx % 2 === 1;
              return (
                <div
                  key={row.id}
                  className={`vst-row ${isEven ? 'vst-row-even' : ''}`}
                  style={{ top: globalIdx * ROW_HEIGHT, height: ROW_HEIGHT }}
                >
                  <div className="vst-cell vst-cell-id">{row.id}</div>
                  <div className="vst-cell vst-cell-name">{row.name}</div>
                  <div className="vst-cell vst-cell-value">{row.value.toFixed(2)}</div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <p className="vst-info">
        显示 {visibleStart + 1}–{visibleEnd} / {sortedData.length} 行 · 排序: {sortKey} {sortDir === 'asc' ? '↑' : '↓'}
      </p>
    </div>
  );
};

export default VirtualScrollTable;

/* ===== CSS Module 内容结束 ===== */
