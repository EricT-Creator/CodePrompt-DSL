import React, { useState, useMemo } from 'react';

interface RowProps { id: number; name: string; email: string; role: string; status: string; }

const mockData: Row[] = [
  { id: 1, name: 'Alice Johnson', email: 'alice@example.com', role: 'Admin', status: 'Active' },
  { id: 2, name: 'Bob Smith', email: 'bob@example.com', role: 'Editor', status: 'Active' },
  { id: 3, name: 'Carol White', email: 'carol@example.com', role: 'Viewer', status: 'Inactive' },
  { id: 4, name: 'Dave Brown', email: 'dave@example.com', role: 'Editor', status: 'Active' },
  { id: 5, name: 'Eve Davis', email: 'eve@example.com', role: 'Admin', status: 'Active' },
  { id: 6, name: 'Frank Miller', email: 'frank@example.com', role: 'Viewer', status: 'Inactive' },
  { id: 7, name: 'Grace Lee', email: 'grace@example.com', role: 'Editor', status: 'Active' },
  { id: 8, name: 'Hank Wilson', email: 'hank@example.com', role: 'Viewer', status: 'Active' },
  { id: 9, name: 'Ivy Chen', email: 'ivy@example.com', role: 'Admin', status: 'Active' },
  { id: 10, name: 'Jack Taylor', email: 'jack@example.com', role: 'Editor', status: 'Inactive' },
  { id: 11, name: 'Kate Anderson', email: 'kate@example.com', role: 'Viewer', status: 'Active' },
  { id: 12, name: 'Leo Martinez', email: 'leo@example.com', role: 'Admin', status: 'Active' },
];

type SortKey = keyof Row;

const DataTable: React.FunctionalComponent = () => {
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('name');
  const [sortAsc, setSortAsc] = useState(true);
  const [page, setPage] = useState(1);
  const perPage = 5;

  const filtered = useMemo(() =>
    mockData.filter(r => Object.values(r).some(v => String(v).toLowerCase().includes(search.toLowerCase()))),
    [search]
  );

  const sorted = useMemo(() =>
    [...filtered].sort((a, b) => {
      const va = String(a[sortKey]).toLowerCase();
      const vb = String(b[sortKey]).toLowerCase();
      return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
    }),
    [filtered, sortKey, sortAsc]
  );

  const totalPages = Math.ceil(sorted.length / perPage);
  const paged = sorted.slice((page - 1) * perPage, page * perPage);

  const toggleSort = (key: SortKey) => {
    if (key === sortKey) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(true); }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-4">Users</h1>
        <input value={search} onChange={e => { setSearch(e.target.value); setPage(1); }}
          placeholder="Search..." className="w-full mb-4 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {(['name', 'email', 'role', 'status'] as SortKey[]).map(key => (
                  <th key={key} onClick={() => toggleSort(key)}
                    className="px-4 py-3 text-left font-medium text-gray-500 cursor-pointer hover:text-gray-800 select-none">
                    {key.charAt(0).toUpperCase() + key.slice(1)} {sortKey === key && (sortAsc ? '↑' : '↓')}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paged.map(r => (
                <tr key={r.id} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{r.name}</td>
                  <td className="px-4 py-3 text-gray-500">{r.email}</td>
                  <td className="px-4 py-3">{r.role}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${r.status === 'Active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                      {r.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-between mt-4 text-sm text-gray-500">
          <span>Showing {(page - 1) * perPage + 1}–{Math.min(page * perPage, sorted.length)} of {sorted.length}</span>
          <div className="flex gap-2">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
              className="px-3 py-1 border rounded disabled:opacity-40">Prev</button>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
              className="px-3 py-1 border rounded disabled:opacity-40">Next</button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DataTable;
