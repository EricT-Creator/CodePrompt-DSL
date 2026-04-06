import React, { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import styles from './VirtualScrollTable.module.css';

interface Row {
  id: number;
  name: string;
  email: string;
  age: number;
  department: string;
}

type SortKey = 'id' | 'name' | 'email' | 'age' | 'department';
type SortDir = 'asc' | 'desc';

const generateRows = (count: number): Row[] => {
  const depts = ['Engineering', 'Marketing', 'Sales', 'HR', 'Finance', 'Design'];
  const firstNames = ['Alice', 'Bob', 'Carol', 'David', 'Eve', 'Frank', 'Grace', 'Henry', 'Iris', 'Jack'];
  const lastNames = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Lopez', 'Wilson'];
  const rows: Row[] = [];
  for (let i = 0; i < count; i++) {
    rows.push({
      id: i + 1,
      name: `${firstNames[i % firstNames.length]} ${lastNames[Math.floor(i / firstNames.length) % lastNames.length]}`,
      email: `${firstNames[i % firstNames.length].toLowerCase()}.${lastNames[Math.floor(i / firstNames.length) % lastNames.length].toLowerCase()}${i}@example.com`,
      age: 20 + (i * 7) % 45,
      department: depts[i % depts.length],
    });
  }
  return rows;
};

const ROW_HEIGHT = 40;
const OVERSCAN = 5;
const TOTAL_ROWS = 10000;

const VirtualScrollTable: React.FC = () => {
  const allRows = useMemo(() => generateRows(TOTAL_ROWS), []);
  const [sortKey, setSortKey] = useState<SortKey>('id');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [scrollTop, setScrollTop] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const sortedRows = useMemo(() => {
    const sorted = [...allRows].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortDir === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      return sortDir === 'asc' ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
    });
    return sorted;
  }, [allRows, sortKey, sortDir]);

  const handleSort = useCallback((key: SortKey) => {
    setSortDir((prev) => (sortKey === key ? (prev === 'asc' ? 'desc' : 'asc') : 'asc'));
    setSortKey(key);
  }, [sortKey]);

  const handleScroll = useCallback(() => {
    if (containerRef.current) {
      setScrollTop(containerRef.current.scrollTop);
    }
  }, []);

  const totalHeight = sortedRows.length * ROW_HEIGHT;
  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - OVERSCAN);
  const endIndex = Math.min(sortedRows.length - 1, Math.ceil((scrollTop + (containerRef.current?.clientHeight ?? 600)) / ROW_HEIGHT) + OVERSCAN);
  const visibleRows = sortedRows.slice(startIndex, endIndex + 1);

  const columns: { key: SortKey; label: string }[] = [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Name' },
    { key: 'email', label: 'Email' },
    { key: 'age', label: 'Age' },
    { key: 'department', label: 'Department' },
  ];

  return (
    <div className={styles.container}>
      <h2 className={styles.title}>Virtual Scroll Table</h2>
      <p className={styles.subtitle}>{sortedRows.length.toLocaleString()} rows | Click headers to sort</p>
      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead className={styles.thead}>
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={`${styles.th} ${sortKey === col.key ? styles.active : ''}`}
                  onClick={() => handleSort(col.key)}
                >
                  {col.label}
                  <span className={styles.sortArrow}>
                    {sortKey === col.key ? (sortDir === 'asc' ? ' ↑' : ' ↓') : ' ↕'}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
        </table>
        <div
          ref={containerRef}
          className={styles.scrollBody}
          onScroll={handleScroll}
        >
          <div style={{ height: totalHeight, position: 'relative' }}>
            {visibleRows.map((row, i) => {
              const rowIndex = startIndex + i;
              return (
                <div
                  key={row.id}
                  className={styles.row}
                  style={{
                    position: 'absolute',
                    top: rowIndex * ROW_HEIGHT,
                    height: ROW_HEIGHT,
                    width: '100%',
                  }}
                >
                  <table className={styles.table}>
                    <tbody>
                      <tr className={styles.tr}>
                        <td className={styles.td}>{row.id}</td>
                        <td className={styles.td}>{row.name}</td>
                        <td className={`${styles.td} ${styles.emailCell}`}>{row.email}</td>
                        <td className={styles.td}>{row.age}</td>
                        <td className={styles.td}>{row.department}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default VirtualScrollTable;

/*
 * VirtualScrollTable.module.css
 */
const cssContent = `
.container {
  max-width: 800px;
  margin: 40px auto;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 4px;
  color: #1a1a1a;
}
.subtitle {
  font-size: 13px;
  color: #888;
  margin-bottom: 16px;
}
.tableWrapper {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}
.table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
.thead {
  background: #f5f5f5;
}
.th {
  padding: 12px 16px;
  text-align: left;
  font-size: 13px;
  font-weight: 600;
  color: #555;
  cursor: pointer;
  user-select: none;
  border-bottom: 2px solid #e0e0e0;
  transition: background 0.15s;
}
.th:hover {
  background: #e8e8e8;
}
.th.active {
  color: #1976d2;
}
.sortArrow {
  margin-left: 4px;
  font-size: 12px;
}
.scrollBody {
  height: 500px;
  overflow-y: auto;
  position: relative;
}
.row {
  box-sizing: border-box;
}
.tr {
  transition: background 0.1s;
}
.tr:hover {
  background: #f9f9f9;
}
.td {
  padding: 8px 16px;
  font-size: 13px;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.emailCell {
  color: #1976d2;
}
`;
