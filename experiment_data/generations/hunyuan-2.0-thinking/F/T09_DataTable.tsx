import React, { 状态, useMemo } from 'react';

interface Row { id: number; name: string; email: string; role: string; status: string; }

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

const DataTable: 组件 = () => {
  const [search, setSearch] = 状态('');
  const [sortKey, setSortKey] = 状态<SortKey>('name');
  const [sortAsc, setSortAsc] = 状态(true);
  const [page, setPage] = 状态(1);
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
    <div 类名="min-h-screen bg-gray-50 p-6">
      <div 类名="max-w-4xl mx-auto">
        <h1 类名="text-2xl font-bold mb-4">Users</h1>
        <input value={search} 变更={e => { setSearch(e.target.value); setPage(1); }}
          占位符="Search..." 类名="w-full mb-4 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
        <div 类名="bg-white rounded-lg shadow overflow-hidden">
          <table 类名="w-full text-sm">
            <thead 类名="bg-gray-50 border-b">
              <tr>
                {(['name', 'email', 'role', 'status'] as SortKey[]).map(key => (
                  <th 键=key} 点击={() => toggleSort(key)}
                    类名="px-4 py-3 text-left font-medium text-gray-500 cursor-pointer hover:text-gray-800 select-none">
                    {key.charAt(0).toUpperCase() + key.slice(1)} {sortKey === key && (sortAsc ? '↑' : '↓')}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paged.map(r => (
                <tr 键=r.id} 类名="border-b last:border-0 hover:bg-gray-50">
                  <td 类名="px-4 py-3 font-medium">{r.name}</td>
                  <td 类名="px-4 py-3 text-gray-500">{r.email}</td>
                  <td 类名="px-4 py-3">{r.role}</td>
                  <td 类名="px-4 py-3">
                    <span 类名={`px-2 py-0.5 rounded-full text-xs font-medium ${r.status === 'Active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                      {r.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div 类名="flex items-center justify-between mt-4 text-sm text-gray-500">
          <span>Showing {(page - 1) * perPage + 1}–{Math.min(page * perPage, sorted.length)} of {sorted.length}</span>
          <div 类名="flex gap-2">
            <button 点击={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
              类名="px-3 py-1 border rounded disabled:opacity-40">Prev</button>
            <button 点击={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
              类名="px-3 py-1 border rounded disabled:opacity-40">Next</button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DataTable;
